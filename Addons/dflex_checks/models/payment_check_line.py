from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexPaymentCheckLine(models.Model):
    _name = "dflex.payment.check.line"
    _description = "Línea de cheque propio en pago"
    _order = "id"

    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="payment_id.company_id", store=True, readonly=True)
    journal_id = fields.Many2one(related="payment_id.journal_id", store=True, readonly=True, string="Diario banco")
    currency_id = fields.Many2one(related="payment_id.currency_id", store=True, readonly=True)
    partner_id = fields.Many2one(related="payment_id.partner_id", store=True, readonly=True, string="Entregado a")

    check_id = fields.Many2one(
        "dflex.check",
        string="Número de cheque",
        required=True,
        domain="[(\"state\", \"=\", \"available\"), (\"company_id\", \"=\", company_id), (\"journal_id\", \"=\", journal_id)]",
        ondelete="restrict",
    )
    check_type = fields.Selection(related="check_id.type", string="Tipo", readonly=True)
    check_state = fields.Selection(related="check_id.state", string="Estado", readonly=True)
    check_payment_date = fields.Date(
        string="Fecha del cheque",
        required=True,
        help="Fecha de pago/vencimiento que se registra en el cheque propio seleccionado.",
    )
    amount = fields.Monetary(string="Importe", required=True)
    note = fields.Char(string="Notas")

    @api.onchange("check_id")
    def _onchange_check_id(self):
        for line in self:
            check = line.check_id
            if not check:
                continue
            if check.payment_date and not line.check_payment_date:
                line.check_payment_date = check.payment_date
            if check.amount and not line.amount:
                line.amount = check.amount

    @api.constrains("check_id", "payment_id", "amount", "check_payment_date")
    def _check_line_consistency(self):
        for line in self:
            payment = line.payment_id
            check = line.check_id
            if not payment or not check:
                continue
            if check.company_id != payment.company_id:
                raise ValidationError(_("El cheque %s pertenece a otra compañía.") % check.display_name)
            if check.journal_id and check.journal_id != payment.journal_id:
                raise ValidationError(
                    _("El cheque %s pertenece al diario %s y no al diario %s.")
                    % (check.display_name, check.journal_id.display_name, payment.journal_id.display_name)
                )
            if check.state != "available" and check.payment_id != payment:
                selection = dict(check._fields["state"].selection)
                raise ValidationError(
                    _("El cheque %s no está en cartera (estado actual: %s).")
                    % (check.display_name, selection.get(check.state, check.state))
                )
            if line.amount <= 0:
                raise ValidationError(_("El importe del cheque propio debe ser mayor a cero."))
            if not line.check_payment_date:
                raise ValidationError(_("Debe indicar la fecha del cheque propio."))

    def unlink(self):
        for line in self:
            check = line.check_id
            payment = line.payment_id
            if check and payment and check.payment_id == payment and check.state == "debited":
                raise ValidationError(_("No se puede quitar el cheque %s porque ya está ingresado.") % check.display_name)
            if check and payment and check.payment_id == payment and check.state in ["delivered", "pending_entry", "returned"]:
                check.write(check._clear_payment_usage_values())
        return super().unlink()
