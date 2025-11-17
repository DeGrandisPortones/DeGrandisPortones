# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Movimiento de cuenta corriente de empleado"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default="/", readonly=True, copy=False)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="restrict", index=True)
    type = fields.Selection([
        ("a", "Anticipo Tipo A (Dinero)"),
        ("b", "Anticipo Tipo B (Alimentos)"),
    ], string="Tipo", required=True, default="a")
    direction = fields.Selection([
        ("out", "Entrega / Salida (pago/anticipo)"),
        ("in", "Devolución / Entrada (descuento)"),
    ], string="Dirección", required=True, default="out",
       help="Salida: anticipo otorgado al empleado. Entrada: reintegro/descuento.")
    amount = fields.Monetary(string="Importe", required=True)
    concept = fields.Text(string="Concepto")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="employee_id.company_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("name", "/") in ("/", False):
                vals["name"] = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        records = super().create(vals_list)
        return records

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)


class HREmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Nº Movimientos", compute="_compute_ledger_stats", store=False)
    ledger_balance = fields.Monetary(string="Saldo CC", compute="_compute_ledger_stats", currency_field="company_currency_id")
    company_currency_id = fields.Many2one("res.currency", string="Moneda", related="company_id.currency_id", readonly=True, store=True)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.direction")
    def _compute_ledger_stats(self):
        for emp in self:
            balance = 0.0
            for mv in emp.ledger_move_ids:
                sign = -1.0 if mv.direction == "out" else 1.0
                balance += sign * (mv.amount or 0.0)
            emp.ledger_balance = balance
            emp.ledger_move_count = len(emp.ledger_move_ids)