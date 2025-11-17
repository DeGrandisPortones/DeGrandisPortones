from odoo import models, fields, api, _

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Employee Ledger Move'
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)
    amount = fields.Monetary(string='Importe', required=True)
    type = fields.Selection([('a','A (Dinero)'),('b','B (Alimentos)')], string='Tipo', required=True, default='a')
    direction = fields.Selection([('to_employee','Pago al empleado'), ('from_employee','Descuento/Devolución')], string='Dirección', required=True, default='to_employee')
    concept = fields.Char(string='Concepto', required=True)
    amount_signed = fields.Monetary(string='Importe con signo', compute='_compute_amount_signed', store=True, currency_field='currency_id')
    state = fields.Selection([('draft','Borrador'),('done','Confirmado')], default='done', string='Estado')

    @api.depends('amount','direction')
    def _compute_amount_signed(self):
        for rec in self:
            sign = 1 if rec.direction == 'to_employee' else -1
            rec.amount_signed = (rec.amount or 0.0) * sign

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, '/', 'New'):
                seq = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or '/'
                vals['name'] = seq
        return super().create(vals)

    def action_print_receipt(self):
        return self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_receipt').report_action(self)

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many('hr.employee.ledger.move','employee_id', string='Movimientos')
    ledger_move_count = fields.Integer(string='Nº Movimientos', compute='_compute_ledger_count')
    ledger_balance = fields.Monetary(string='Saldo Cuenta Corriente', compute='_compute_ledger_balance', currency_field='ledger_currency_id')
    ledger_currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)

    def _compute_ledger_count(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def _compute_ledger_balance(self):
        for emp in self:
            emp.ledger_balance = sum(emp.ledger_move_ids.mapped('amount_signed'))