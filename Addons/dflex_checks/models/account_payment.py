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

    
    def _dflex_get_checks_from_payment(self):
        """Obtiene todos los dflex.check vinculados a este pago:
        - Por campo dflex_check_id (compatibilidad)
        - Por detalles l10n_latam.check con payment_id = pago y dflex_check_id cargado
        """
        self.ensure_one()
        checks = self.env["dflex.check"]
        if self.dflex_check_id:
            checks |= self.dflex_check_id

        l10n_checks = self.env["l10n_latam.check"].search(
            [("payment_id", "=", self.id), ("dflex_check_id", "!=", False)]
        )
        checks |= l10n_checks.mapped("dflex_check_id")
        return checks

    def action_post(self):
        """Al contabilizar el pago, marcar como entregado todos los cheques DFlex vinculados al pago."""
        res = super().action_post()
        for payment in self:
            for check in payment._dflex_get_checks_from_payment():
                # Evita que el mismo cheq ue se use en múltiples pagos.
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

                vals = {"state": "delivered", "payment_id": payment.id}
                # Completar datos de operación para reporting (proveedor / importe)
                if "partner_id" in check._fields and payment.partner_id:
                    vals["partner_id"] = payment.partner_id.id
                if "amount" in check._fields:
                    # El cheque suele representar el valor entregado con el pago
                    vals["amount"] = abs(payment.amount)
                if "currency_id" in check._fields and getattr(payment, "currency_id", False):
                    vals["currency_id"] = payment.currency_id.id

                check.write(vals)
        return res


    
    def action_cancel(self):
        res = super().action_cancel()
        for payment in self:
            for check in payment._dflex_get_checks_from_payment():
                if check.payment_id == payment and check.state == "delivered":
                    check.write({"state": "available", "payment_id": False})
        return res


    def action_dflex_mark_check_returned(self):
        """Marcar los cheques del pago como devueltos/rechazados."""
        for payment in self:
            for check in payment._dflex_get_checks_from_payment():
                if check.payment_id == payment and check.state == "delivered":
                    check.write({"state": "returned"})
        return True
