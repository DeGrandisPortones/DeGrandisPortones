from odoo import api, fields, models

class AccountPaymentCheckLine(models.Model):
    _name = "account.payment.check.line"
    _description = "Cheque recibido en pago"
    _order = "id desc"

    payment_id = fields.Many2one("account.payment", ondelete="cascade", required=True)
    number = fields.Char("Número de cheque")
    bank_id = fields.Many2one("res.bank", string="Banco")
    issuer = fields.Char("Emisor (titular)")
    issuer_vat = fields.Char("CUIT Emisor")
    issue_date = fields.Date("Fecha de emisión")
    payment_date = fields.Date("Fecha de pago")
    due_date = fields.Date("Fecha de vencimiento")
    amount = fields.Monetary("Importe")
    currency_id = fields.Many2one(related="payment_id.currency_id", store=True, readonly=True)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_line_ids = fields.One2many("account.payment.check.line", "payment_id", string="Cheques")
    has_checks = fields.Boolean(compute="_compute_has_checks", string="Tiene cheques")

    @api.depends("check_line_ids")
    def _compute_has_checks(self):
        for rec in self:
            rec.has_checks = bool(rec.check_line_ids)