
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "RRHH - Pseudo movimiento (A/B)"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Número", readonly=True, copy=False, default="New")
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda s: s.env.company)

    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    payment_type = fields.Selection([("a","Pago A (dinero)"),("b","Pago B (alimentos)")], required=True, default="a", string="Tipo de pago")
    account_src_id = fields.Many2one("account.account", string="Cuenta de salida (caja/banco)", domain=[("deprecated","=",False)], required=True)
    amount = fields.Monetary(string="Importe", required=True, default=0.0, currency_field="currency_id")
    concept = fields.Char(string="Concepto abonado", required=True)
    narration = fields.Text(string="Notas")
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True, default=lambda s: s.env.company.currency_id)

    state = fields.Selection([("draft","Borrador"),("posted","Asentado"),("cancel","Cancelado")], default="draft", string="Estado")

    account_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True, copy=False)
    batch_account_move_id = fields.Many2one("account.move", string="Asiento mensual", readonly=True, copy=False)
    batch_id = fields.Many2one("hr.employee.ledger.batch", string="Lote mensual", readonly=True, copy=False)

    @api.constrains("amount")
    def _check_amount(self):
        for m in self:
            if (m.amount or 0.0) <= 0.0:
                raise ValidationError(_("El importe debe ser mayor a 0."))

    def action_post(self):
        for m in self:
            if m.state != "draft":
                raise UserError(_("Solo se pueden asentar movimientos en borrador."))
            if m.name in (False, "New"):
                seq = self.env.ref("hr_employee_ledger.seq_hr_employee_ledger_move", raise_if_not_found=False)
                m.name = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
            m.state = "posted"
        return True

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger.action_report_employee_payment_receipt').report_action(self)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, string="Moneda compañía")
    ledger_balance = fields.Monetary(string="Saldo CC Empleado", currency_field="company_currency_id", compute="_compute_ledger_balance")
    ledger_move_count = fields.Integer(string="Movimientos CC", compute="_compute_ledger_balance")

    def _compute_ledger_balance(self):
        Move = self.env["hr.employee.ledger.move"]
        for emp in self:
            moves = Move.search([("employee_id","=", emp.id), ("state","=","posted")])
            emp.ledger_balance = sum(m.amount for m in moves)
            emp.ledger_move_count = len(moves)

    def action_view_employee_ledger(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger.action_hr_employee_ledger_move").read()[0]
        action["domain"] = [("employee_id","=", self.id)]
        action["context"] = {"default_employee_id": self.id, "search_default_employee_id": self.id}
        return action
