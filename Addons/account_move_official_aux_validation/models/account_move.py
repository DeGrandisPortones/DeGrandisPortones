from odoo import _, api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_manual_journal_entry(self):
        """Heurística para considerar "manual" (creado desde Asientos contables).

        - Si move_type != 'entry' => NO es manual.
        - Si es 'entry' y está vinculado a un documento/origen típico (payment, stock, asset, etc.) => NO es manual.
        - Caso contrario => manual.

        Nota: usamos getattr/fields para no depender de módulos opcionales.
        """
        self.ensure_one()

        if self.move_type != "entry":
            return False

        origin_fields = [
            # account
            "payment_id",
            "asset_id",
            "tax_cash_basis_origin_move_id",
            # stock_account
            "stock_move_id",
            # purchase / sale (a veces generan entry)
            "purchase_id",
            "sale_order_id",
        ]
        for fname in origin_fields:
            if fname in self._fields and self[fname]:
                return False

        return True

    def _has_mix_1_5_and_6_9(self):
        """True si el asiento mezcla cuentas cuyo código inicia en 1-5 con cuentas 6-9."""
        self.ensure_one()
        g1 = set("12345")
        g2 = set("6789")

        has_g1 = False
        has_g2 = False

        for line in self.line_ids.filtered(lambda l: not l.display_type and l.account_id):
            code = (line.account_id.code or "").strip()
            if not code:
                continue
            first = code[0]
            if first in g1:
                has_g1 = True
            elif first in g2:
                has_g2 = True
            if has_g1 and has_g2:
                return True
        return False

    def _mix_warning_dict(self):
        return {
            "title": _("Incongruencia de cuentas"),
            "message": _(
                "Este asiento manual mezcla cuentas con código 1–5 con cuentas 6–9.\n"
                "Es recomendable no realizarlo."
            ),
        }

    def action_post(self):
        """NO bloquea. Postea normalmente y, si corresponde, muestra notificación en UI."""
        res = super().action_post()

        # Mostramos la notificación como acción cliente para garantizar que se vea al postear.
        for move in self:
            if move._is_manual_journal_entry() and move._has_mix_1_5_and_6_9():
                payload = move._mix_warning_dict()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": payload["title"],
                        "message": payload["message"],
                        "type": "warning",
                        "sticky": True,
                    },
                }

        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("account_id", "debit", "credit")
    def _onchange_mix_accounts_warning(self):
        """Warning no bloqueante mientras se edita el asiento (en borrador)."""
        for line in self:
            move = line.move_id
            if not move:
                continue
            if not move._is_manual_journal_entry():
                continue
            if move._has_mix_1_5_and_6_9():
                return {"warning": move._mix_warning_dict()}
        return {}
