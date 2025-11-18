from odoo import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_balance = fields.Monetary(string="Saldo CC Empleado",
                                     currency_field="company_currency_id",
                                     compute="_compute_ledger_balance",
                                     readonly=True, store=False)

    company_currency_id = fields.Many2one('res.currency', string="Moneda compañía",
                                          related="company_id.currency_id", readonly=True, store=True)

    @api.depends('company_id')
    def _compute_ledger_balance(self):
        Move = self.env['hr.employee.ledger.move'].sudo()
        for emp in self:
            moves = Move.search([('employee_id', '=', emp.id)])
            debit = sum(m.amount for m in moves if m.direction == 'debit')
            credit = sum(m.amount for m in moves if m.direction == 'credit')
            emp.ledger_balance = debit - credit