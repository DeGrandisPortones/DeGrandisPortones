# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", readonly=True, copy=False, default="/")
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="cascade", index=True)
    type = fields.Selection(
        [
            ("payment", "Abono"),
            ("charge", "Cargo"),
        ],
        string="Tipo",
        required=True,
        default="payment",
    )
    concept = fields.Char(string="Concepto", required=True)
    amount = fields.Monetary(string="Importe", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)

class Employee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Detalle de movimientos")
    ledger_move_count = fields.Integer(string="Movimientos", compute="_compute_ledger_stats", store=False)
    ledger_balance = fields.Monetary(string="Saldo", compute="_compute_ledger_stats", currency_field="currency_id", store=False)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
        store=False,
    )

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.type")
    def _compute_ledger_stats(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)
            balance = 0.0
            for m in emp.ledger_move_ids:
                balance += m.amount if m.type == "payment" else -m.amount
            emp.ledger_balance = balance

    def action_open_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.action_employee_ledger_moves").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        ctx = dict(self._context or {})
        ctx.update({"search_default_employee_id": self.id, "default_employee_id": self.id})
        action["context"] = ctx
        return action
