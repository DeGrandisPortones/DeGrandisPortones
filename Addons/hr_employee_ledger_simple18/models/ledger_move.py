from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Employee Ledger Move'
    _order = 'date desc, id desc'

    name = fields.Char(string='Número', readonly=True, copy=False)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, index=True)
    type = fields.Selection([('a', 'A (Dinero)'), ('b', 'B (Alimentos)')], string='Tipo', required=True, default='a')
    direction = fields.Selection([('out', 'Adelanto'), ('in', 'Descuento')], string='Movimiento', required=True, default='out')
    amount = fields.Monetary(string='Importe', required=True)
    concept = fields.Char(string='Concepto')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref('hr_employee_ledger_simple18.seq_hr_employee_ledger_move')
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = seq.next_by_id()
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.report_employee_ledger_move_receipt').report_action(self)
