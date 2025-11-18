
from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos (CC)")
    ledger_move_count = fields.Integer(string="Movimientos", compute="_compute_ledger_stats", store=False)
    ledger_balance = fields.Monetary(string="Saldo CC", currency_field="currency_id", compute="_compute_ledger_stats", store=False)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.type", "ledger_move_ids.direction")
    def _compute_ledger_stats(self):
        for emp in self:
            count = len(emp.ledger_move_ids)
            balance = 0.0
            for m in emp.ledger_move_ids:
                sign = 1.0
                # Simple rule: Entrada suma, Salida resta
                if m.direction == "out":
                    sign = -1.0
                balance += sign * (m.amount or 0.0)
            emp.ledger_move_count = count
            emp.ledger_balance = balance

    def action_open_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.action_employee_ledger_moves").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action
