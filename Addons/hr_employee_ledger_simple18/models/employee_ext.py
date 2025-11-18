from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Movimientos", compute="_compute_ledger_totals")
    ledger_balance = fields.Monetary(string="Saldo", compute="_compute_ledger_totals",
                                     currency_field="ledger_currency_id", readonly=True)
    ledger_currency_id = fields.Many2one("res.currency", related="company_id.currency_id",
                                         store=True, readonly=True)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.direction")
    def _compute_ledger_totals(self):
        for emp in self:
            moves = emp.ledger_move_ids
            emp.ledger_move_count = len(moves)
            balance = 0.0
            for m in moves:
                balance += m.amount if m.direction == "in" else -m.amount
            emp.ledger_balance = balance
