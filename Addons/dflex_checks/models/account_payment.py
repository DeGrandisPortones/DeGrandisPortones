from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque",
        domain="[(\"state\", \"=\", \"available\"), (\"company_id\", \"=\", company_id)]",
        help="Cheque a entregar con este pago.",
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado de emisión",
        store=True,
        readonly=True,
    )

    @api.constrains("dflex_check_id", "company_id")
    def _constrains_dflex_check_company(self):
        for payment in self:
            if payment.dflex_check_id and payment.dflex_check_id.company_id != payment.company_id:
                raise ValidationError(_("El cheque seleccionado pertenece a otra compañía."))

    def action_post(self):
        """Al contabilizar el pago, si se cargó un cheque de cartera, marcarlo como entregado."""
        res = super().action_post()
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue

            # Evita que el mismo cheque se use en múltiples pagos.
            if check.payment_id and check.payment_id != payment:
                raise ValidationError(
                    _("El cheque %s ya está vinculado al pago %s.")
                    % (check.display_name, check.payment_id.display_name)
                )

            if check.state != "available":
                selection = dict(check._fields["state"].selection)
                raise ValidationError(
                    _("El cheque %s no está disponible (estado actual: %s).")
                    % (check.display_name, selection.get(check.state, check.state))
                )

            check.write({"state": "delivered", "payment_id": payment.id})
        return res

    def action_cancel(self):
        """Si se cancela el pago, liberar el cheque (si lo había reservado/entregado este pago)."""
        res = super().action_cancel()
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue

            if check.payment_id == payment and check.state == "delivered":
                check.write({"state": "available", "payment_id": False})
        return res

    def action_dflex_mark_check_returned(self):
        """Marcar el cheque del pago como devuelto/rechazado."""
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue

            if check.payment_id and check.payment_id != payment:
                raise ValidationError(
                    _("El cheque %s está vinculado a otro pago (%s).")
                    % (check.display_name, check.payment_id.display_name)
                )

            if check.state != "delivered":
                selection = dict(check._fields["state"].selection)
                raise ValidationError(
                    _("Solo se puede marcar como Devuelto un cheque en estado Entregado. Estado actual: %s")
                    % selection.get(check.state, check.state)
                )

            check.write({"state": "returned", "payment_id": payment.id})
        return True
