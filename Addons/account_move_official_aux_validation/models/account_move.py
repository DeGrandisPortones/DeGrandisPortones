from odoo import _, models
from odoo.exceptions import ValidationError


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

    def _check_official_aux_accounts_mix(self):
        """Regla:
        - Si el asiento NO es manual:
          no se permite mezclar cuentas con código que empiece en 1-4 (oficiales)
          con cuentas que empiecen en 5-7 (auxiliares).
        """
        official_prefixes = set("1234")
        aux_prefixes = set("567")

        for move in self:
            if move._is_manual_journal_entry():
                continue

            has_official = False
            has_aux = False

            for line in move.line_ids.filtered(lambda l: not l.display_type):
                code = (line.account_id.code or "").strip()
                if not code:
                    continue
                first = code[0]
                if first in official_prefixes:
                    has_official = True
                elif first in aux_prefixes:
                    has_aux = True

                if has_official and has_aux:
                    raise ValidationError(
                        _(
                            "Validación contable: no se permite mezclar cuentas oficiales (1-4) con auxiliares (5-7) "
                            "en asientos que NO fueron creados desde 'Asientos Contables'.\n\n"
                            "Asiento: %s\nDiario: %s"
                        )
                        % (move.display_name, move.journal_id.display_name)
                    )

    def action_post(self):
        # Si el usuario ya confirmó, no bloqueamos el posteo.
        if self.env.context.get("official_aux_validation_confirmed"):
            return super().action_post()

        try:
            self._check_official_aux_accounts_mix()
        except ValidationError as e:
            # En procesos no interactivos (cron / import / scripts) mantenemos el comportamiento actual: bloquear.
            if not self.env.context.get("params"):
                raise

            wiz = self.env["official.aux.validation.confirm.wizard"].create(
                {
                    "move_ids": [(6, 0, self.ids)],
                    "message": _(
                        "El movimiento presenta una incongruencia entre las cuentas contables "
                        "(mezcla de cuentas oficiales 1-4 y auxiliares 5-7).\n\n"
                        "¿Deseas continuar?\n\n"
                        "Detalle:\n%s"
                    )
                    % str(e),
                }
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("Confirmación"),
                "res_model": "official.aux.validation.confirm.wizard",
                "view_mode": "form",
                "res_id": wiz.id,
                "target": "new",
            }

        return super().action_post()
