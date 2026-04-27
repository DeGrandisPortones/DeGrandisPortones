from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque propio",
        domain="[(\"state\", \"=\", \"available\"), (\"company_id\", \"=\", company_id)]",
        help="Cheque propio disponible a entregar con este pago.",
        copy=False,
    )
    dflex_check_payment_date = fields.Date(
        string="Fecha del cheque",
        copy=False,
        help="Fecha de pago/vencimiento que se registra en el cheque propio seleccionado.",
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado cheque propio",
        store=True,
        readonly=True,
    )

    def _dflex_is_own_check_payment(self):
        self.ensure_one()
        return self.payment_type == "outbound" and self.payment_method_line_id.code == "own_checks"

    @api.onchange("payment_method_line_id", "payment_type")
    def _onchange_dflex_check_payment_method(self):
        for payment in self:
            if payment.dflex_check_id and not payment._dflex_is_own_check_payment():
                payment.dflex_check_id = False
                payment.dflex_check_payment_date = False

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id(self):
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue
            if check.payment_date and not payment.dflex_check_payment_date:
                payment.dflex_check_payment_date = check.payment_date

    @api.constrains("dflex_check_id", "company_id", "payment_type", "payment_method_line_id")
    def _constrains_dflex_check(self):
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue
            if check.company_id != payment.company_id:
                raise ValidationError(_("El cheque seleccionado pertenece a otra compañía."))
            if not payment._dflex_is_own_check_payment():
                raise ValidationError(
                    _("Los cheques propios de chequera solo pueden usarse en pagos salientes con método Own Checks.")
                )

    def _dflex_validate_checks_before_post(self):
        for payment in self.filtered("dflex_check_id"):
            check = payment.dflex_check_id

            if not payment._dflex_is_own_check_payment():
                raise ValidationError(
                    _("El cheque propio %s solo puede usarse con el método de pago Own Checks.") % check.display_name
                )

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

    def _dflex_write_delivered_checks(self):
        for payment in self.filtered("dflex_check_id"):
            check = payment.dflex_check_id
            check.write(
                {
                    "state": "delivered",
                    "payment_id": payment.id,
                    "move_id": payment.move_id.id or False,
                    "issue_date": payment.date,
                    "payment_date": payment.dflex_check_payment_date or payment.date,
                    "delivery_date": fields.Date.context_today(payment),
                    "amount": payment.amount,
                    "currency_id": payment.currency_id.id,
                    "partner_id": payment.partner_id.id or False,
                }
            )

    def _dflex_release_checks(self):
        for payment in self.filtered("dflex_check_id"):
            check = payment.dflex_check_id
            if check.payment_id != payment:
                continue
            if check.state == "debited":
                raise ValidationError(_("No se puede liberar el cheque %s porque ya fue debitado.") % check.display_name)
            check.write(
                {
                    "state": "available",
                    "payment_id": False,
                    "move_id": False,
                    "issue_date": False,
                    "payment_date": False,
                    "delivery_date": False,
                    "amount": 0.0,
                    "partner_id": False,
                }
            )

    def action_post(self):
        self._dflex_validate_checks_before_post()
        res = super().action_post()
        self._dflex_write_delivered_checks()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._dflex_release_checks()
        return res

    def action_draft(self):
        res = super().action_draft()
        self._dflex_release_checks()
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
