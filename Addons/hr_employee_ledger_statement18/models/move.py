from odoo import models, fields, api

class HrEmployeeLedgerMove(models.Model):
    _inherit = "hr.employee.ledger.move"

    debit = fields.Float(string="Débito", compute="_compute_debit_credit", store=False)
    credit = fields.Float(string="Crédito", compute="_compute_debit_credit", store=False)
    running_balance = fields.Float(string="Saldo", compute="_compute_running_balance", store=False)

    @api.depends('type', 'amount')
    def _compute_debit_credit(self):
        for rec in self:
            t = (rec.type or '').lower()
            if t in ('charge', 'cargo'):
                rec.debit = rec.amount or 0.0
                rec.credit = 0.0
            else:
                rec.debit = 0.0
                rec.credit = rec.amount or 0.0

    def _compute_running_balance(self):
        # Compute cumulative balance per employee, starting at opening (before date_from, if provided)
        # Get context
        date_from = self.env.context.get('statement_date_from')
        # group records by employee
        by_emp = {}
        for r in self:
            by_emp.setdefault(r.employee_id.id, []).append(r)
        for emp_id, recs in by_emp.items():
            recs.sort(key=lambda r: (r.date or fields.Date.today(), r.id))
            opening = 0.0
            if date_from:
                # sum of signed amounts strictly before date_from
                moves = self.search([('employee_id', '=', emp_id), ('date', '<', date_from)])
                for m in moves:
                    t = (m.type or '').lower()
                    opening += (m.amount or 0.0) * (1 if t in ('charge', 'cargo') else -1)
            balance = opening
            for r in recs:
                balance += (r.debit - r.credit)
                r.running_balance = balance