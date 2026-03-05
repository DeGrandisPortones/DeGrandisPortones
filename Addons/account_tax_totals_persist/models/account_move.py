# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @api.model
    def _extract_tax_amounts_by_group(self, tax_totals):
        """Return a {tax_group_id: tax_amount_currency} mapping from a tax_totals dict."""
        res = {}
        if not tax_totals:
            return res

        # Expected structure (core): tax_totals['subtotals'][...]['tax_groups'][...]
        for subtotal in (tax_totals.get("subtotals") or []):
            for tg in (subtotal.get("tax_groups") or []):
                tg_id = tg.get("id")
                if tg_id:
                    res[tg_id] = tg.get("tax_amount_currency")
        return res

    def _apply_tax_amounts_by_group(self, amounts_by_group):
        """Re-apply tax totals amounts (per tax group) through the tax_totals inverse."""
        if not amounts_by_group:
            return

        for move in self:
            if not move.tax_totals:
                continue

            totals = move.tax_totals
            changed = False
            for subtotal in (totals.get("subtotals") or []):
                for tg in (subtotal.get("tax_groups") or []):
                    tg_id = tg.get("id")
                    if tg_id in amounts_by_group and amounts_by_group[tg_id] is not None:
                        # Only overwrite if different, to reduce noise/recomputations.
                        if tg.get("tax_amount_currency") != amounts_by_group[tg_id]:
                            tg["tax_amount_currency"] = amounts_by_group[tg_id]
                            changed = True

            if changed:
                # Writing on tax_totals triggers the inverse, which adjusts the corresponding tax lines.
                move.with_context(skip_tax_totals_persist=True).tax_totals = totals

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange("invoice_date", "date", "partner_id", "fiscal_position_id")
    def _onchange_preserve_tax_totals_on_date_change(self):
        """Preserve tax group amounts when changing invoice/bill date in draft.

        Odoo recomputes tax lines when the document date changes (e.g., due to currency rate
        or localization logic). For localizations where some tax groups are manually adjusted
        from the tax totals widget (e.g., AR perceptions), that recomputation may reset those
        manual values. This onchange re-applies the previous tax group amounts from the
        origin record.
        """
        if self.env.context.get("skip_tax_totals_persist"):
            return

        for move in self:
            if not move.is_invoice(include_receipts=True) or move.state != "draft":
                continue
            if not move._origin or not move._origin.tax_totals:
                continue

            old_map = self._extract_tax_amounts_by_group(move._origin.tax_totals)
            move._apply_tax_amounts_by_group(old_map)

    # -------------------------------------------------------------------------
    # ORM overrides
    # -------------------------------------------------------------------------


    def write(self, vals):
        if self.env.context.get("skip_tax_totals_persist"):
            return super().write(vals)

        vals = vals or {}
        vals_keys = set(vals)

        # Cases we preserve:
        # 1) Fixing dates (typical AR perception reset case).
        date_only_keys = {"invoice_date", "date", "invoice_date_due"}
        preserve_on_date = bool(vals_keys & {"invoice_date", "date"}) and vals_keys.issubset(date_only_keys)

        # 2) Changing partner/fiscal position/payment terms (partner onchange can also reset dynamic tax lines).
        partner_only_keys = {"partner_id", "partner_shipping_id", "fiscal_position_id", "invoice_payment_term_id", "invoice_date_due"}
        preserve_on_partner = bool(vals_keys & {"partner_id", "fiscal_position_id"}) and vals_keys.issubset(partner_only_keys)

        preserve = preserve_on_date or preserve_on_partner

        snapshots = {}
        if preserve:
            moves = self.filtered(
                lambda m: m.state == "draft"
                and m.is_invoice(include_receipts=True)
                and m.tax_totals
            )
            snapshots = {m.id: self._extract_tax_amounts_by_group(m.tax_totals) for m in moves}

        res = super().write(vals)

        if preserve and snapshots:
            moves = self.filtered(lambda m: m.id in snapshots)
            for m in moves:
                m._apply_tax_amounts_by_group(snapshots.get(m.id))

        return res
