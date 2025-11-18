from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Nº Movimientos", compute="_compute_ledger_stats", store=False)
    ledger_balance = fields.Monetary(string="Saldo", currency_field="ledger_currency_id", compute="_compute_ledger_stats", store=False)
    ledger_currency_id = fields.Many2one("res.currency", readonly=True, compute="_compute_ledger_currency", store=False)

    @api.depends("company_id")
    def _compute_ledger_currency(self):
        for rec in self:
            rec.ledger_currency_id = rec.company_id.currency_id.id or self.env.company.currency_id.id

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.direction")
    def _compute_ledger_stats(self):
        for rec in self:
            balance = 0.0
            for m in rec.ledger_move_ids:
                balance += (m.amount or 0.0) if m.direction == "in" else -(m.amount or 0.0)
            rec.ledger_balance = balance
            rec.ledger_move_count = len(rec.ledger_move_ids)