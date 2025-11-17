from odoo import api, fields, models

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move', 'employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Nº Movs', compute='_compute_ledger_stats', store=False)
    ledger_balance = fields.Monetary(string='Saldo', compute='_compute_ledger_stats', currency_field='ledger_currency_id', store=False)
    ledger_currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', readonly=True)

    @api.depends('ledger_move_ids.amount', 'ledger_move_ids.direction')
    def _compute_ledger_stats(self):
        for emp in self:
            balance = 0.0
            for line in emp.ledger_move_ids:
                balance += line.amount if line.direction == 'in' else -line.amount
            emp.ledger_move_count = len(emp.ledger_move_ids)
            emp.ledger_balance = balance
