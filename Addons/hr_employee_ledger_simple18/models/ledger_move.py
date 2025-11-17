from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Employee Ledger Move'
    _order = 'date desc, id desc'

    name = fields.Char(string='Número', readonly=True, default='New', copy=False)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    type = fields.Selection([
        ('a', 'Anticipo dinero (A)'),
        ('b', 'Anticipo alimentos (B)'),
    ], string='Tipo', required=True, default='a')
    direction = fields.Selection([
        ('debit', 'Debe (paga empresa)'),
        ('credit', 'Haber (devuelve empleado)'),
    ], string='Dirección', required=True, default='debit')
    concept = fields.Text(string='Concepto')
    amount = fields.Monetary(string='Importe', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='employee_id.company_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', related='employee_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = self.env['ir.sequence'].with_context(
                    force_company=self.env.company.id
                ).next_by_code('hr.employee.ledger.move') or _('New')
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.employee_ledger_move_receipt_action').report_action(self)