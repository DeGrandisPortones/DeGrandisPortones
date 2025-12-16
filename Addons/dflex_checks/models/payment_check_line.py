from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPaymentDflexCheckLine(models.Model):
    _name = "account.payment.dflex.check.line"
    _description = "Cheque en pago (DFlex)"
    _order = "id desc"

    payment_id = fields.Many2one("account.payment", string="Pago", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="payment_id.company_id", store=True, readonly=True)

    check_id = fields.Many2one(
        "dflex.check",
        string="Cheque",
        required=True,
        domain="[('state', '=', 'available'), ('company_id', '=', company_id), ('payment_id', '=', False)]",
        help="Cheque en cartera a entregar con este pago.",
    )

    check_state = fields.Selection(related="check_id.state", string="Estado", store=True, readonly=True)
    bank_id = fields.Many2one(related="check_id.bank_id", string="Banco", readonly=True)
    type = fields.Selection(related="check_id.type", string="Tipo", readonly=True)
    issue_date = fields.Date(related="check_id.issue_date", string="Fecha Emisión", readonly=True)

    currency_id = fields.Many2one(related="check_id.currency_id", readonly=True)
    amount = fields.Monetary(related="check_id.amount", currency_field="currency_id", string="Importe", readonly=True)

    partner_id = fields.Many2one(related="check_id.partner_id", string="Proveedor", readonly=True)

    _sql_constraints = [
        ("unique_check_per_payment", "unique(payment_id, check_id)", "El cheque ya está cargado en este pago."),
    ]

    @api.constrains("check_id", "payment_id")
    def _check_check_not_used_in_other_payment(self):
        for line in self:
            if not line.check_id or not line.payment_id:
                continue
            if line.check_id.payment_id and line.check_id.payment_id != line.payment_id:
                raise ValidationError(
                    _("El cheque %s está vinculado a otro pago (%s).")
                    % (line.check_id.display_name, line.check_id.payment_id.display_name)
                )
