
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Employee Ledger Move'
    _order = 'date desc, id desc'

    name = fields.Char(string='Número', default='/', readonly=True)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, index=True, ondelete='cascade')
    type = fields.Selection([('a', 'Tipo A (Dinero)'), ('b', 'Tipo B (Alimentos)')], string='Tipo', required=True, default='a')
    direction = fields.Selection([('out', 'Egreso'), ('in', 'Ingreso')], string='Dirección', required=True, default='out')
    amount = fields.Monetary(string='Importe', required=True)
    concept = fields.Text(string='Concepto')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='employee_id.company_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', related='employee_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') in (False, '/', ''):
                seq = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or '/'
                vals['name'] = seq
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.employee_ledger_move_receipt_action').report_action(self)

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move', 'employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Movimientos', compute='_compute_ledger_counts')
    ledger_balance = fields.Monetary(string='Saldo', compute='_compute_ledger_balance', currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Moneda compañía', related='company_id.currency_id', readonly=True)

    def _compute_ledger_counts(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def _compute_ledger_balance(self):
        for emp in self:
            balance = 0.0
            for m in emp.ledger_move_ids:
                balance += m.amount if m.direction == 'in' else -m.amount
            emp.ledger_balance = balance

    def action_open_employee_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_moves').read()[0]
        action['domain'] = [('employee_id', '=', self.id)]
        action.setdefault('context', {})
        action['context'].update({'default_employee_id': self.id})
        return action
