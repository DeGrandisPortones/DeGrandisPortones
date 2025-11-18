from odoo import api, fields, models

class HrEmployeeLedgerStatementWizard(models.TransientModel):
    _name = 'hr.employee.ledger.statement.wizard'
    _description = 'Employee Ledger Statement Wizard'

    employee_id = fields.Many2one('hr.employee', required=True, string='Empleado')
    date_from = fields.Date(required=True, string='Desde', default=lambda self: fields.Date.to_date(fields.Date.today().replace(day=1)))
    date_to = fields.Date(required=True, string='Hasta', default=fields.Date.today)

    def action_view_statement(self):
        self.ensure_one()
        action = self.env.ref('hr_employee_ledger_statement18.action_employee_ledger_statement_result').read()[0]
        action['domain'] = [
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        ctx = dict(self.env.context or {})
        ctx.update({
            'search_default_employee_id': self.employee_id.id,
            'default_employee_id': self.employee_id.id,
            'statement_date_from': self.date_from and self.date_from.strftime('%Y-%m-%d'),
            'statement_date_to': self.date_to and self.date_to.strftime('%Y-%m-%d'),
        })
        action['context'] = ctx
        return action


class HrEmployeeLedgerMove(models.Model):
    _inherit = 'hr.employee.ledger.move'

    debit = fields.Float(string='Débito', compute='_compute_debit_credit', store=False)
    credit = fields.Float(string='Crédito', compute='_compute_debit_credit', store=False)
    running_balance = fields.Float(string='Saldo', compute='_compute_running_balance', store=False)

    @api.depends('type', 'amount')
    def _compute_debit_credit(self):
        for rec in self:
            if rec.type == 'charge':
                rec.debit = rec.amount or 0.0
                rec.credit = 0.0
            elif rec.type == 'payment':
                rec.debit = 0.0
                rec.credit = rec.amount or 0.0
            else:
                rec.debit = 0.0
                rec.credit = 0.0

    @api.depends('employee_id', 'date', 'debit', 'credit')
    def _compute_running_balance(self):
        for rec in self:
            balance = 0.0
            if rec.employee_id and rec.date:
                domain = [('employee_id', '=', rec.employee_id.id),
                          '|', ('date', '<', rec.date), ('date', '=', rec.date)]
                moves = rec.search(domain, order='date,id')
                for m in moves:
                    if m.type == 'charge':
                        balance += (m.amount or 0.0)
                    elif m.type == 'payment':
                        balance -= (m.amount or 0.0)
            rec.running_balance = balance
