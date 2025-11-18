
from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id")
    ledger_move_count = fields.Integer(compute="_compute_ledger_counts", store=False)
    ledger_balance = fields.Monetary(compute="_compute_ledger_balance", currency_field="ledger_currency_id", store=False)
    ledger_currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.direction")
    def _compute_ledger_balance(self):
        for emp in self:
            total = 0.0
            for m in emp.ledger_move_ids:
                total += m.amount if m.direction == "in" else -m.amount
            emp.ledger_balance = total

    def _compute_ledger_counts(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def action_open_ledger_moves(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": "Movimientos",
            "res_model": "hr.employee.ledger.move",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
            "target": "current",
        }
        return action
