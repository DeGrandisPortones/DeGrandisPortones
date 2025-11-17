# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move','employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Nº Movimientos', compute='_compute_ledger_stats', store=False)
    ledger_balance = fields.Monetary(string='Saldo', compute='_compute_ledger_stats', currency_field='ledger_currency_id', store=False)
    ledger_currency_id = fields.Many2one('res.currency', string='Moneda', compute='_compute_ledger_currency', store=False)

    @api.depends('company_id')
    def _compute_ledger_currency(self):
        for rec in self:
            rec.ledger_currency_id = rec.company_id.currency_id

    @api.depends('ledger_move_ids.amount', 'ledger_move_ids.direction')
    def _compute_ledger_stats(self):
        for emp in self:
            count = len(emp.ledger_move_ids)
            balance = 0.0
            for mv in emp.ledger_move_ids:
                balance += mv.amount if mv.direction == 'out' else -mv.amount
            emp.ledger_move_count = count
            emp.ledger_balance = balance

    def action_open_ledger_moves(self):
        self.ensure_one()
        return {
            'type':'ir.actions.act_window',
            'name': _('Movimientos'),
            'res_model': 'hr.employee.ledger.move',
            'view_mode': 'list,form',
            'domain': [('employee_id','=', self.id)],
            'context': {'default_employee_id': self.id},
            'target': 'current',
        }

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Movimiento de Cuenta Corriente de Empleado'
    _order = 'date desc, id desc'

    name = fields.Char(string='Nº', readonly=True, copy=False)
    date = fields.Date(required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', string='Empleado')
    type = fields.Selection([
        ('money','Anticipo Dinero (A)'),
        ('food','Anticipo Alimentos (B)')
    ], required=True, default='money', string='Tipo')
    direction = fields.Selection([
        ('out','Entrega/Anticipo'),
        ('in','Devolución/Descuento')
    ], required=True, default='out', string='Sentido')
    amount = fields.Monetary(required=True, string='Monto')
    currency_id = fields.Many2one('res.currency', related='employee_id.company_id.currency_id', store=False, readonly=True)
    concept = fields.Char(string='Concepto')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or '/'
        return super().create(vals)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_move_receipt').report_action(self)
