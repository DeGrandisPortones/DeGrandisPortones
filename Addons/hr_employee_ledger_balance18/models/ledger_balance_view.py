from odoo import api, fields, models, tools

class HrEmployeeLedgerBalance(models.Model):
    _name = "hr.employee.ledger.balance"
    _description = "Employee Ledger Running Balance (SQL view)"
    _auto = False
    _order = "employee_id, date, move_id"

    move_id = fields.Many2one("hr.employee.ledger.move", string="Movimiento", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", index=True, readonly=True)
    date = fields.Date(string="Fecha", readonly=True)
    type = fields.Selection([("charge", "Cargo"), ("payment", "Abono")], string="Tipo", readonly=True)
    concept = fields.Char(string="Concepto", readonly=True)
    amount = fields.Float(string="Importe", digits=(16, 2), readonly=True)
    signed_amount = fields.Float(string="Importe (+/-)", digits=(16, 2), readonly=True)
    running_balance = fields.Float(string="Saldo", digits=(16, 2), readonly=True)

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, "hr_employee_ledger_balance")
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW hr_employee_ledger_balance AS
            SELECT
                m.id                AS id,
                m.id                AS move_id,
                m.employee_id       AS employee_id,
                m.date              AS date,
                m.type              AS type,
                m.concept           AS concept,
                m.amount            AS amount,
                CASE WHEN m.type = 'charge' THEN m.amount ELSE -m.amount END AS signed_amount,
                SUM(CASE WHEN m.type = 'charge' THEN m.amount ELSE -m.amount END)
                    OVER (PARTITION BY m.employee_id ORDER BY m.date, m.id
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_balance
            FROM hr_employee_ledger_move m
            """
        )