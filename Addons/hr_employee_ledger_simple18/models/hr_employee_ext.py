# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move', 'employee_id', string='Movimientos')
    ledger_currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)
    ledger_balance = fields.Monetary(string='Saldo cuenta corriente', currency_field='ledger_currency_id', compute='_compute_ledger_balance', store=False)
    ledger_move_count = fields.Integer(string='Movimientos', compute='_compute_ledger_counts')

    def _compute_ledger_counts(self):
        data = self.env['hr.employee.ledger.move'].read_group(
            domain=[('employee_id', 'in', self.ids)],
            fields=['employee_id'],
            groupby=['employee_id'],
        )
        mapped = {d['employee_id'][0]: d['employee_id_count'] for d in data}
        for emp in self:
            emp.ledger_move_count = mapped.get(emp.id, 0)

    def _compute_ledger_balance(self):
        data = self.env['hr.employee.ledger.move'].read_group(
            domain=[('employee_id', 'in', self.ids)],
            fields=['amount_signed:sum'],
            groupby=['employee_id'],
        )
        sums = {d['employee_id'][0]: d['amount_signed_sum'] for d in data}
        for emp in self:
            emp.ledger_balance = sums.get(emp.id, 0.0)

    def action_open_ledger_moves(self):
        self.ensure_one()
        return {
            'name': 'Cuenta corriente',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.ledger.move',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
