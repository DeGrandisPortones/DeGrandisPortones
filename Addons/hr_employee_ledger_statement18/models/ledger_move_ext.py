
from odoo import models, fields, api

class HrEmployeeLedgerMove(models.Model):
    _inherit = "hr.employee.ledger.move"

    debit = fields.Monetary(string="Débito", currency_field="company_currency_id", compute="_compute_amount_columns", store=False)
    credit = fields.Monetary(string="Crédito", currency_field="company_currency_id", compute="_compute_amount_columns", store=False)
    running_balance = fields.Monetary(string="Saldo", currency_field="company_currency_id", compute="_compute_running_balance", store=False)

    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends('type', 'amount')
    def _compute_amount_columns(self):
        for rec in self:
            code = (rec.type or '').lower()
            is_charge = code in ('charge', 'cargo')
            is_payment = code in ('payment', 'abono')
            debit = rec.amount if is_charge else 0.0
            credit = rec.amount if is_payment else 0.0
            rec.debit = debit
            rec.credit = credit

    def _compute_running_balance(self):
        # Running balance over filtered set, optionally starting from an initial balance provided by context.
        # Context keys accepted:
        # - statement_employee_id: int (required for accurate running)
        # - statement_date_from: date (optional)
        # The balance is computed as sum(charges) - sum(payments).
        # For performance and accurate ordering, we use a single SQL window function.
        if not self:
            return
        # Group records by employee for correctness (usually one employee due to domain)
        by_emp = {}
        for rec in self:
            by_emp.setdefault(rec.employee_id.id, []).append(rec.id)
        cr = self.env.cr
        for emp_id, ids in by_emp.items():
            # Build window balance for all moves of this employee ordered by date, id
            cr.execute("""
                SELECT m.id,
                       SUM(CASE
                               WHEN LOWER(m.type) IN ('charge','cargo') THEN m.amount
                               WHEN LOWER(m.type) IN ('payment','abono') THEN -m.amount
                               ELSE 0
                           END) OVER (PARTITION BY m.employee_id ORDER BY m.date, m.id)
                FROM hr_employee_ledger_move m
                WHERE m.employee_id = %s
                  AND m.id = ANY(%s)
            """, (emp_id, ids))
            rows = dict(cr.fetchall()) if cr.rowcount else {}
            # If a date_from is provided, subtract the employee balance strictly before that date
            ctx = self.env.context or {}
            date_from = ctx.get('statement_date_from')
            initial = 0.0
            if date_from:
                cr.execute("""
                    SELECT COALESCE(SUM(CASE
                               WHEN LOWER(type) IN ('charge','cargo') THEN amount
                               WHEN LOWER(type) IN ('payment','abono') THEN -amount
                               ELSE 0 END), 0.0)
                    FROM hr_employee_ledger_move
                    WHERE employee_id = %s AND date < %s
                """, (emp_id, date_from))
                initial = cr.fetchone()[0] or 0.0
            recs = self.browse(ids)
            for r in recs:
                bal = rows.get(r.id, 0.0) - initial
                r.running_balance = bal
