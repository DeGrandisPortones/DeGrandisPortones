from odoo import api, fields, models

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move', 'employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Movimientos', compute='_compute_ledger_stats')
    ledger_currency_id = fields.Many2one('res.currency', string='Moneda', compute='_compute_ledger_currency', store=False)
    ledger_balance = fields.Monetary(string='Saldo', currency_field='ledger_currency_id', compute='_compute_ledger_stats', store=False)

    @api.depends('company_id')
    def _compute_ledger_currency(self):
        for emp in self:
            emp.ledger_currency_id = emp.company_id.currency_id

    def _compute_ledger_stats(self):
        for emp in self:
            balance = 0.0
            for m in emp.ledger_move_ids:
                if m.direction == 'debit':
                    balance += m.amount or 0.0
                else:
                    balance -= m.amount or 0.0
            emp.ledger_move_count = len(emp.ledger_move_ids)
            emp.ledger_balance = balance

    def action_open_employee_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_moves').read()[0]
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action