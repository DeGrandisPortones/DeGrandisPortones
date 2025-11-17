
from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Movimiento de cuenta corriente de empleado"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default="New", readonly=True, copy=False)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="cascade", index=True)
    type = fields.Selection([("a", "Tipo A (Dinero)"), ("b", "Tipo B (Alimentos)")], string="Tipo", required=True, default="a")
    direction = fields.Selection([("out", "Entrega (Anticipo)"), ("in", "Descuento (Devolución)")], string="Movimiento", required=True, default="out")
    amount = fields.Monetary(string="Importe", required=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", related="employee_id.company_id.currency_id", store=True, readonly=True)
    concept = fields.Char(string="Concepto")

    type_label = fields.Char(string="Tipo (etiqueta)", compute="_compute_labels", store=False)
    direction_label = fields.Char(string="Movimiento (etiqueta)", compute="_compute_labels", store=False)

    @api.depends("type", "direction")
    def _compute_labels(self):
        for rec in self:
            rec.type_label = "Tipo A (Dinero)" if rec.type == "a" else "Tipo B (Alimentos)"
            rec.direction_label = "Entrega (Anticipo)" if rec.direction == "out" else "Descuento (Devolución)"

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                if seq:
                    vals["name"] = seq.next_by_id()
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)


class HREmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Nº Movimientos", compute="_compute_ledger_stats", compute_sudo=True)
    ledger_currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True, readonly=True)
    ledger_balance = fields.Monetary(string="Saldo", currency_field="ledger_currency_id", compute="_compute_ledger_stats", compute_sudo=True)

    def _compute_ledger_stats(self):
        Move = self.env["hr.employee.ledger.move"].sudo()
        for emp in self:
            moves = Move.search([("employee_id", "=", emp.id)])
            emp.ledger_move_count = len(moves)
            balance = 0.0
            for m in moves:
                balance += (m.amount if m.direction == "in" else -m.amount)
            emp.ledger_balance = balance
