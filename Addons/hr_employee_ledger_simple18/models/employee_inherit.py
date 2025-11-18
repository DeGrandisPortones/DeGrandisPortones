from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many(
        "hr.employee.ledger.move",
        "employee_id",
        string="Movimientos",
    )
    ledger_move_count = fields.Integer(
        string="Movimientos",
        compute="_compute_ledger_counters",
        store=False,
    )
    ledger_balance = fields.Monetary(
        string="Saldo",
        compute="_compute_ledger_balance",
        currency_field="currency_id",
        store=False,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.depends("ledger_move_ids")
    def _compute_ledger_counters(self):
        for rec in self:
            rec.ledger_move_count = len(rec.ledger_move_ids)

    @api.depends("ledger_move_ids.amount", "ledger_move_ids.type", "ledger_move_ids.direction")
    def _compute_ledger_balance(self):
        for rec in self:
            balance = 0.0
            for m in rec.ledger_move_ids:
                # Simple rule: abono/in = +, cargo/out = - (ajústese a la lógica real)
                sign = 1.0 if m.type == "abono" else -1.0
                balance += sign * (m.amount or 0.0)
            rec.ledger_balance = balance

    def action_open_ledger(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.action_employee_ledger_moves").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {
            "default_employee_id": self.id,
            "search_default_employee_id": self.id,
        }
        return action