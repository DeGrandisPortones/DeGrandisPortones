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
    type = fields.Selection(
        [("fisico", "Físico"), ("echeq", "eCheq")],
        string="Tipo de cheque",
        required=True,
        default="fisico",
        help="Indica si la chequera/cartera contiene cheques físicos o cheques electrónicos.",
    )

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
            ("available", "En Cartera"),
            ("delivered", "Entregado"),
            ("pending_entry", "Por ingresar"),
            ("debited", "Ingresado"),
            ("returned", "Devuelto"),
            ("cancelled", "Anulado"),
        ],
        string="Estado",
        default="available",
        index=True,
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
            "name": _("Cheques propios en cartera"),
            "res_model": "dflex.check",
            "view_mode": "list,form",
            "domain": [("state", "=", "available")],
            "context": {"search_default_available": 1},
        }

    def _is_payment_reconciled_in_bank(self):
        self.ensure_one()
        payment = self.payment_id
        if not payment:
            return False

        # En Odoo 18/AR, el pago suele pasar a paid cuando queda conciliado.
        if payment.state == "paid":
            return True

        move = payment.move_id
        if not move:
            return False

        bank_or_cash_lines = move.line_ids.filtered(lambda line: line.account_id.account_type == "asset_cash")
        if not bank_or_cash_lines:
            bank_or_cash_lines = move.line_ids.filtered(lambda line: line.journal_id.type in ["bank", "cash"])

        return bool(bank_or_cash_lines.filtered(lambda line: line.reconciled))

    def _get_state_from_dates_and_payment(self):
        self.ensure_one()
        if self.state in ["available", "returned", "cancelled"]:
            return self.state

        if self._is_payment_reconciled_in_bank():
            return "debited"

        today = fields.Date.context_today(self)
        if self.payment_date and self.payment_date <= today:
            return "pending_entry"

        return "delivered"

    def _update_operational_state(self):
        for check in self.filtered(lambda c: c.state in ["delivered", "pending_entry", "debited"]):
            new_state = check._get_state_from_dates_and_payment()
            if new_state != check.state:
                check.state = new_state

    @api.model
    def _cron_update_check_states(self):
        checks = self.search([("state", "in", ["delivered", "pending_entry"]), ("payment_id", "!=", False)])
        checks._update_operational_state()
        return True

    def action_update_operational_state(self):
        records = self if self else self.search([("state", "in", ["delivered", "pending_entry"]), ("payment_id", "!=", False)])
        records._update_operational_state()
        return True

    # Acciones de estado
    def action_deliver(self):
        for check in self:
            if check.state != "available":
                raise ValidationError(_("Solo se pueden entregar cheques en estado En Cartera."))
            check.state = "delivered"

    def action_pending_entry(self):
        for check in self:
            if check.state != "delivered":
                raise ValidationError(_("Solo se pueden marcar Por ingresar cheques en estado Entregado."))
            check.state = "pending_entry"

    def action_debit(self):
        for check in self:
            if check.state not in ["delivered", "pending_entry"]:
                raise ValidationError(_("Solo se pueden marcar como Ingresados cheques Entregados o Por ingresar."))
            check.state = "debited"

    def action_cancel(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede anular un cheque ya ingresado."))
            check.state = "cancelled"

    def action_return(self):
        """Marca el cheque como devuelto/rechazado."""
        for check in self:
            if check.state not in ["delivered", "pending_entry"]:
                raise ValidationError(_("Solo se pueden marcar como Devueltos cheques Entregados o Por ingresar."))
            check.state = "returned"

    def action_reset_available(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede volver a En Cartera un cheque ya ingresado."))
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
