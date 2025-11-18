
from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Movimientos", compute="_compute_ledger_totals", store=False)
    ledger_balance = fields.Monetary(string="Saldo", compute="_compute_ledger_totals", currency_field="ledger_currency_id", store=False)
    ledger_currency_id = fields.Many2one("res.currency", string="Moneda", compute="_compute_ledger_currency", store=False)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.direction")
    def _compute_ledger_totals(self):
        for emp in self:
            balance = 0.0
            for m in emp.ledger_move_ids:
                balance += m.amount if m.direction == "in" else -m.amount
            emp.ledger_balance = balance
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def _compute_ledger_currency(self):
        for emp in self:
            emp.ledger_currency_id = emp.company_id.currency_id
