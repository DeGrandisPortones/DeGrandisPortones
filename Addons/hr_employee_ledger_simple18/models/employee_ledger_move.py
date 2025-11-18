from odoo import api, fields, models, _

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Movimiento de cuenta corriente empleado"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", readonly=True, default="/", copy=False)
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", related="company_id.currency_id", store=True, readonly=True)

    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True, ondelete="restrict")

    type = fields.Selection([('a', 'Tipo A (Dinero)'), ('b', 'Tipo B (Alimentos)')],
                            string="Tipo", required=True, default='a')
    direction = fields.Selection([('debit', 'Cargo (+)'), ('credit', 'Abono (–)')],
                                 string="Dirección", required=True, default='debit')

    amount = fields.Monetary(string="Importe", currency_field="currency_id", required=True, default=0.0)
    concept = fields.Char(string="Concepto", required=False)
    note = fields.Text(string="Notas")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.ledger.move') or '/'
        recs = super().create(vals_list)
        return recs