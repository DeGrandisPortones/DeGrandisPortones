from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheck(models.Model):
    _name = "dflex.check"
    _description = "Cheque propio"
    _order = "issue_date desc, id desc"
    _rec_name = "name"

    # Datos principales
    name = fields.Char(string="N° Cheque", required=True, index=True, copy=False)
    number = fields.Integer(string="Número", required=True, index=True)
    checkbook_id = fields.Many2one("dflex.checkbook", string="Chequera", ondelete="restrict")
    bank_id = fields.Many2one("res.bank", string="Banco", required=True)
    type = fields.Selection([("fisico", "Físico"), ("echeq", "eCheq")], string="Tipo", required=True)

    # Fechas e importes
    issue_date = fields.Date(string="Fecha Emisión")
    payment_date = fields.Date(string="Fecha Pago")
    amount = fields.Monetary(string="Importe")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)

    # Proveedor
    partner_id = fields.Many2one("res.partner", string="Proveedor")
    cuit_proveedor = fields.Char(string="CUIT Proveedor", related="partner_id.vat", store=True)
    partner_name = fields.Char(string="Razón Social Proveedor", related="partner_id.name", store=True)

    # Estado del ciclo del cheque
    state = fields.Selection(
        [
            ("available", "Disponible"),
            ("delivered", "Entregado"),
            ("returned", "Devuelto"),
            ("debited", "Debitado"),
            ("cancelled", "Anulado"),
        ],
        string="Estado",
        default="available",
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company, required=True
    )

    available_bank_ids = fields.Many2many(
        "res.bank",
        string="Bancos disponibles",
        compute="_compute_available_bank_ids",
        compute_sudo=True,
    )


    # Auditoría
    move_id = fields.Many2one("account.move", string="Asiento relacionado", readonly=True)
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago relacionado",
        readonly=True,
        copy=False,
        help="Pago en el que este cheque fue utilizado/entregado.",
    )
    note = fields.Text(string="Notas")

    _sql_constraints = [
        (
            "unique_check_per_bank_company",
            "unique(number, bank_id, company_id)",
            "Ya existe un cheque con ese número para este banco y compañía.",
        )
    ]

    # Acciones de estado
@api.depends("company_id")
def _compute_available_bank_ids(self):
    Journal = self.env["account.journal"].sudo()
    PartnerBank = self.env["res.partner.bank"].sudo()
    for rec in self:
        banks = self.env["res.bank"]
        if rec.company_id:
            journals = Journal.search([("company_id", "=", rec.company_id.id), ("type", "=", "bank")])
            banks |= journals.mapped("bank_account_id.bank_id")
            banks |= PartnerBank.search([("company_id", "=", rec.company_id.id)]).mapped("bank_id")
        rec.available_bank_ids = banks or self.env["res.bank"].sudo().search([])


    def action_deliver(self):
        for check in self:
            if check.state != "available":
                raise ValidationError(_("Solo se pueden entregar cheques en estado Disponible."))
            check.state = "delivered"

    def action_debit(self):
        for check in self:
            if check.state != "delivered":
                raise ValidationError(_("Solo se pueden debitar cheques en estado Entregado."))
            check.state = "debited"

    def action_cancel(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede anular un cheque ya debitado."))
            check.state = "cancelled"

    def action_return(self):
        """Marca el cheque como devuelto/rechazado."""
        for check in self:
            if check.state != "delivered":
                raise ValidationError(_("Solo se pueden marcar como Devueltos cheques en estado Entregado."))
            check.state = "returned"

    def action_reset_available(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede volver a Disponible un cheque ya debitado."))
            check.state = "available"
            check.payment_id = False

    # Conveniencia
    @api.onchange("number")
    def _onchange_number(self):
        for rec in self:
            if rec.number:
                rec.name = str(rec.number)
