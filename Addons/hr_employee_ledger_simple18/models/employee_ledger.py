from odoo import models, fields, api, _

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    ledger_move_ids = fields.One2many(
        'hr.employee.ledger.move', 'employee_id', string='Movimientos CC'
    )
    ledger_move_count = fields.Integer(
        compute='_compute_ledger_counters', string='Movs CC'
    )
    ledger_balance = fields.Monetary(
        compute='_compute_ledger_counters', string='Saldo CC',
        currency_field='ledger_currency_id'
    )
    ledger_currency_id = fields.Many2one(
        'res.currency', compute='_compute_ledger_currency', string='Moneda', readonly=True
    )

    def _compute_ledger_currency(self):
        for rec in self:
            rec.ledger_currency_id = (rec.company_id or self.env.company).currency_id

    def _compute_ledger_counters(self):
        for rec in self:
            moves = rec.ledger_move_ids
            rec.ledger_move_count = len(moves)
            balance = 0.0
            for m in moves:
                sign = 1.0 if m.direction == 'out' else -1.0
                balance += sign * (m.amount or 0.0)
            rec.ledger_balance = balance

    def action_hr_employee_ledger_moves(self):
        self.ensure_one()
        action = self.env.ref('hr_employee_ledger_simple18.action_hr_employee_ledger_moves').read()[0]
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action


class EmployeeLedgerMove(models.Model):
    _name = 'hr.employee.ledger.move'
    _description = 'Movimiento Cuenta Corriente Empleado'
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', default='New', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    type = fields.Selection([('money', 'Dinero'), ('food', 'Alimentos')], string='Tipo', required=True, default='money')
    direction = fields.Selection([('out', 'Entrega al empleado'), ('in', 'Descuento/Devolución')], string='Movimiento', required=True, default='out')
    concept = fields.Char(string='Concepto')
    amount = fields.Monetary(string='Importe', required=True)
    currency_id = fields.Many2one('res.currency', related='employee_id.company_id.currency_id', store=False, readonly=True)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger_simple18.action_employee_ledger_move_receipt').report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        IrSeq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') in ('New', '/', False):
                vals['name'] = IrSeq.next_by_code('hr.employee.ledger.move') or _('New')
        return super().create(vals_list)