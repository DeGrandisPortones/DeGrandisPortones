# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrEmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Movimiento cuenta corriente empleado'
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Número', default='Nuevo', required=True, copy=False)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='restrict')
    move_kind = fields.Selection([('a', 'Tipo A (Dinero)'), ('b', 'Tipo B (Alimentos)')], string='Tipo', required=True, default='a')
    direction = fields.Selection([('advance', 'Anticipo/Entrega (+)'), ('deduction', 'Descuento/Devolución (-)')], string='Dirección', required=True, default='advance')
    concept = fields.Char(string='Concepto', required=True)
    amount = fields.Monetary(string='Importe', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)
    amount_signed = fields.Monetary(string='Importe firmado', currency_field='currency_id', compute='_compute_amount_signed', store=False)
    note = fields.Text(string='Notas')
    receipt_printed = fields.Boolean(string='Recibo impreso', default=False, help='Marcado cuando se imprime el recibo.')

    @api.depends('amount', 'direction')
    def _compute_amount_signed(self):
        for rec in self:
            if rec.direction == 'deduction':
                rec.amount_signed = -abs(rec.amount or 0.0)
            else:
                rec.amount_signed = abs(rec.amount or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref('hr_employee_ledger.sequence_hr_employee_ledger_move', raise_if_not_found=False)
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nuevo':
                if seq:
                    vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or _('Nuevo')
                else:
                    vals['name'] = _('Nuevo')
        return super().create(vals_list)
