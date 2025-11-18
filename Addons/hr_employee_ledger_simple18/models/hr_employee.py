from odoo import api, fields, models

class HREmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(compute="_compute_ledger_counts", string="Movimientos")
    ledger_balance = fields.Monetary(compute="_compute_ledger_balance", string="Saldo", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True, store=True)

    def _compute_ledger_counts(self):
        data = self.env["hr.employee.ledger.move"].read_group(
            [("employee_id","in", self.ids)], ["employee_id"], ["employee_id"]
        )
        mapped = {d["employee_id"][0]: d["employee_id_count"] for d in data}
        for rec in self:
            rec.ledger_move_count = mapped.get(rec.id, 0)

    def _compute_ledger_balance(self):
        for rec in self:
            moves = self.env["hr.employee.ledger.move"].search([("employee_id","=",rec.id)])
            balance = 0.0
            for m in moves:
                sign = 1 if m.direction == "in" else -1
                balance += sign * (m.amount or 0.0)
            rec.ledger_balance = balance

    def action_open_ledger_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Movimientos",
            "res_model": "hr.employee.ledger.move",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
            "target": "current",
        }