from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheck(models.Model):
    _name = "dflex.check"
    _description = "Cheque propio"
    _order = "number asc, id asc"
    _rec_name = "name"

    # Datos principales
    name = fields.Char(string="N° Cheque", required=True, index=True, copy=False)
    number = fields.Integer(string="Número", required=True, index=True)
    checkbook_id = fields.Many2one("dflex.checkbook", string="Chequera", ondelete="restrict")
    bank_id = fields.Many2one("res.bank", string="Banco", required=True)
    type = fields.Selection([("fisico", "Físico"), ("echeq", "eCheq")], string="Tipo", required=True)

    # Fechas e importes
    issue_date = fields.Date(string="Fecha Emisión")
    payment_date = fields.Date(string="Fecha de pago")
    delivery_date = fields.Date(
        string="Fecha entrega",
        readonly=True,
        copy=False,
        help="Fecha en la que el cheque propio se entregó mediante un pago.",
    )
    amount = fields.Monetary(string="Importe")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)

    # Proveedor / destinatario
    partner_id = fields.Many2one("res.partner", string="Entregado a")
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
    )

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company, required=True
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
        ),
    ]

    def _get_available_action(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Cheques propios disponibles"),
            "res_model": "dflex.check",
            "view_mode": "list,form",
            "domain": [("state", "=", "available")],
            "context": {"search_default_available": 1},
        }

    # Acciones de estado
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

    # Conveniencia
    @api.onchange("number")
    def _onchange_number(self):
        for rec in self:
            if rec.number:
                rec.name = str(rec.number)
