# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class Employee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many(
        "hr.employee.ledger.move", "employee_id", string="Movimientos"
    )
    ledger_move_count = fields.Integer(
        string="Movimientos", compute="_compute_ledger_stats"
    )
    ledger_balance = fields.Monetary(
        string="Saldo CC", compute="_compute_ledger_stats", currency_field="company_currency_id", readonly=True
    )
    company_currency_id = fields.Many2one(
        "res.currency", string="Moneda", compute="_compute_company_currency", readonly=True
    )

    @api.depends("company_id")
    def _compute_company_currency(self):
        for emp in self:
            emp.company_currency_id = emp.company_id.currency_id.id or self.env.company.currency_id.id

    def _compute_ledger_stats(self):
        for emp in self:
            moves = self.env["hr.employee.ledger.move"].sudo().search([("employee_id", "=", emp.id)])
            emp.ledger_move_count = len(moves)
            # credit (entrada) suma, debit (salida) resta
            balance = sum(m.amount if m.direction == "in" else -m.amount for m in moves)
            emp.ledger_balance = balance

    def action_open_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.action_employee_ledger_moves").read()[0]
        action.setdefault("domain", []).append(("employee_id", "=", self.id))
        action.setdefault("context", {})
        action["context"].update({
            "default_employee_id": self.id,
        })
        return action


class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Movimiento Cuenta Corriente Empleado"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default="/", readonly=True, copy=False)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    type = fields.Selection([("a", "A - Dinero"), ("b", "B - Alimentos")], string="Tipo", required=True, default="a")
    direction = fields.Selection([("in", "Entrada (A favor)"), ("out", "Salida (A cuenta)")], string="Dirección", required=True, default="out")
    concept = fields.Char(string="Concepto", required=True)
    amount = fields.Monetary(string="Importe", required=True)
    currency_id = fields.Many2one("res.currency", related="employee_id.company_id.currency_id", store=False, readonly=True)

    @api.model
    def create(self, vals):
        # set sequence
        if vals.get("name", "/") in ("/", False):
            vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        # fallback: if created desde formulario de empleado sin default explícito
        ctx = self.env.context or {}
        if not vals.get("employee_id") and ctx.get("active_model") == "hr.employee" and ctx.get("active_id"):
            vals["employee_id"] = ctx["active_id"]
        return super().create(vals)

    def action_print_receipt(self):
        self.ensure_one()
        # Report action must exist with this xmlid
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)
