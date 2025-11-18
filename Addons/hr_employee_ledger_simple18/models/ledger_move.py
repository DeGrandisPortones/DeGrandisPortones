from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Number", default="New", readonly=True, required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, ondelete="cascade")
    type = fields.Selection([
        ("payment", "Pago"),
        ("charge", "Cargo"),
    ], required=True, default="payment")
    direction = fields.Selection([
        ("in", "Entrada"),
        ("out", "Salida"),
    ], required=True, default="in")
    concept = fields.Char()
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", related="employee_id.company_id.currency_id", store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or _("New")
        return super().create(vals_list)

    def action_print_receipt(self):
        # Use a safe ref to the report action; ensure xml id exists
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)


class HREmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(compute="_compute_ledger_stats", string="Movimientos")
    ledger_balance = fields.Monetary(compute="_compute_ledger_stats", currency_field="currency_id", string="Saldo")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", string="Moneda", readonly=True)

    def _compute_ledger_stats(self):
        for emp in self:
            total = 0.0
            for m in emp.ledger_move_ids:
                total += m.amount if m.direction == "in" else -m.amount
            emp.ledger_move_count = len(emp.ledger_move_ids)
            emp.ledger_balance = total
