import copy

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _extract_tax_amounts_by_group(self, tax_totals):
        res = {}
        if not tax_totals:
            return res
        for subtotal in (tax_totals.get("subtotals") or []):
            for tax_group in (subtotal.get("tax_groups") or []):
                group_id = tax_group.get("id")
                if group_id:
                    res[group_id] = tax_group.get("tax_amount_currency")
        return res

    def _get_perception_tax_group_ids(self):
        self.ensure_one()
        return set(
            self.fiscal_position_id.l10n_ar_tax_ids.filtered(lambda x: x.tax_type == "perception")
            .mapped("default_tax_id.tax_group_id.id")
        )

    @api.model
    def _recompute_tax_totals_amounts(self, totals):
        if not totals:
            return totals

        subtotal_amount_currency_sum = 0.0
        subtotal_amount_sum = 0.0
        for subtotal in (totals.get("subtotals") or []):
            tax_groups = subtotal.get("tax_groups") or []
            if "tax_amount_currency" in subtotal:
                subtotal["tax_amount_currency"] = sum((group.get("tax_amount_currency") or 0.0) for group in tax_groups)
                subtotal_amount_currency_sum += subtotal["tax_amount_currency"]
            if "tax_amount" in subtotal:
                subtotal["tax_amount"] = sum((group.get("tax_amount") or 0.0) for group in tax_groups)
                subtotal_amount_sum += subtotal["tax_amount"]

        if "tax_amount_currency" in totals:
            totals["tax_amount_currency"] = subtotal_amount_currency_sum
        if "tax_amount" in totals:
            totals["tax_amount"] = subtotal_amount_sum
        if "total_amount_currency" in totals and "base_amount_currency" in totals:
            totals["total_amount_currency"] = (totals.get("base_amount_currency") or 0.0) + subtotal_amount_currency_sum
        if "total_amount" in totals and "base_amount" in totals:
            totals["total_amount"] = (totals.get("base_amount") or 0.0) + subtotal_amount_sum
        return totals

    @api.model
    def _zero_new_perception_groups(self, tax_totals, old_amounts_by_group, perception_group_ids):
        if not tax_totals or not perception_group_ids:
            return tax_totals, False

        totals = copy.deepcopy(tax_totals)
        changed = False
        for subtotal in (totals.get("subtotals") or []):
            for tax_group in (subtotal.get("tax_groups") or []):
                group_id = tax_group.get("id")
                if group_id not in perception_group_ids:
                    continue

                current_amount = tax_group.get("tax_amount_currency")
                old_amount = old_amounts_by_group.get(group_id)

                is_new_group = group_id not in old_amounts_by_group or old_amount is None
                is_default_one = current_amount in (1, 1.0)
                if is_new_group and is_default_one:
                    tax_group["tax_amount_currency"] = 0.0
                    if "tax_amount" in tax_group:
                        tax_group["tax_amount"] = 0.0
                    changed = True

        if changed:
            totals = self._recompute_tax_totals_amounts(totals)
        return totals, changed

    @api.onchange("tax_totals", "fiscal_position_id")
    def _onchange_zero_new_perception_groups(self):
        if self.env.context.get("skip_l10n_ar_perception_zero_default"):
            return

        for move in self.filtered(lambda m: m.state == "draft" and m.is_invoice(include_receipts=True) and m.tax_totals):
            perception_group_ids = move._get_perception_tax_group_ids()
            if not perception_group_ids:
                continue

            old_map = move._extract_tax_amounts_by_group(move._origin.tax_totals or {})
            totals, changed = move._zero_new_perception_groups(move.tax_totals, old_map, perception_group_ids)
            if changed:
                move.with_context(skip_l10n_ar_perception_zero_default=True).tax_totals = totals

    def write(self, vals):
        if self.env.context.get("skip_l10n_ar_perception_zero_default"):
            return super().write(vals)

        watch_tax_totals = "tax_totals" in (vals or {})
        snapshots = {}
        if watch_tax_totals:
            for move in self.filtered(lambda m: m.state == "draft" and m.is_invoice(include_receipts=True) and m.tax_totals):
                perception_group_ids = move._get_perception_tax_group_ids()
                if perception_group_ids:
                    snapshots[move.id] = {
                        "old_map": move._extract_tax_amounts_by_group(move.tax_totals),
                        "perception_group_ids": perception_group_ids,
                    }

        res = super().write(vals)

        if watch_tax_totals and snapshots:
            for move in self.filtered(lambda m: m.id in snapshots and m.state == "draft" and m.tax_totals):
                data = snapshots[move.id]
                totals, changed = move._zero_new_perception_groups(
                    move.tax_totals,
                    data["old_map"],
                    data["perception_group_ids"],
                )
                if changed:
                    move.with_context(skip_l10n_ar_perception_zero_default=True).tax_totals = totals

        return res
