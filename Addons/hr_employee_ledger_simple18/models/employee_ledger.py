# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HREmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many(
        "hr.employee.ledger.move", "employee_id", string="Movimientos CC"
    )
    ledger_move_count = fields.Integer(
        compute="_compute_ledger_counts", string="Nº Movs", store=False
    )
    ledger_balance = fields.Monetary(
        compute="_compute_ledger_balance", currency_field="ledger_currency_id", string="Saldo CC", store=False
    )
    ledger_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )

    def _compute_ledger_counts(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def _compute_ledger_balance(self):
        for emp in self:
            balance = 0.0
            for m in emp.ledger_move_ids:
                sign = 1 if m.direction == "in" else -1
                balance += sign * (m.amount or 0.0)
            emp.ledger_balance = balance


class HREmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default="New", copy=False, readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="cascade")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    type = fields.Selection(
        selection=[("a", "A - Dinero"), ("b", "B - Alimentos")], string="Tipo", required=True, default="a"
    )
    direction = fields.Selection(
        selection=[("in", "Pago al empleado"), ("out", "Descuento / Devolución")],
        string="Dirección",
        required=True,
        default="in",
    )
    concept = fields.Char(string="Concepto", required=True)
    amount = fields.Monetary(string="Importe", required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", string="Moneda", related="employee_id.company_id.currency_id", store=True, readonly=True
    )
    company_id = fields.Many2one(related="employee_id.company_id", store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                if seq:
                    vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or _("New")
                else:
                    vals["name"] = _("New")
        return super().create(vals_list)

    def action_view_employee_moves(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.action_hr_employee_ledger_moves").read()[0]
        action["domain"] = [("employee_id", "=", self.employee_id.id)]
        return action
