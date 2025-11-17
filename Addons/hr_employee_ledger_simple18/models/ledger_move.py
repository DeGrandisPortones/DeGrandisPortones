# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Employee Ledger Move'
    _order = 'date desc, id desc'

    name = fields.Char(string='Número', readonly=True, copy=False, default='/')
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, index=True,
                                  ondelete='cascade')
    type = fields.Selection([('a', 'A - Dinero'), ('b', 'B - Alimentos')], string='Tipo', required=True)
    direction = fields.Selection([('debit', 'Pago / Adelanto'), ('credit', 'Descuento / Nómina')],
                                 string='Sentido', required=True, default='debit')
    amount = fields.Monetary(string='Monto', required=True)
    concept = fields.Text(string='Concepto')
    company_id = fields.Many2one('res.company', string='Compañía',
                                 related='employee_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda',
                                  related='company_id.currency_id', store=True, readonly=True)

    _sql_constraints = [
        ('amount_positive', 'CHECK(amount > 0)', 'El monto debe ser mayor que cero.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                seq = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or '/'
                vals['name'] = seq
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_move_receipt').report_action(self)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move', 'employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Movimientos', compute='_compute_ledger_counters')
    ledger_balance = fields.Monetary(string='Saldo (a descontar)',
                                     currency_field='company_currency_id',
                                     compute='_compute_ledger_counters')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    def _compute_ledger_counters(self):
        for rec in self:
            moves = rec.ledger_move_ids
            rec.ledger_move_count = len(moves)
            debit = sum(m.amount for m in moves if m.direction == 'debit')
            credit = sum(m.amount for m in moves if m.direction == 'credit')
            rec.ledger_balance = debit - credit  # >0 significa deuda del empleado a la compañía

    def action_open_ledger_moves(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Movimientos'),
            'res_model': 'hr.employee.ledger.move',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
            'target': 'current',
        }
        return action
