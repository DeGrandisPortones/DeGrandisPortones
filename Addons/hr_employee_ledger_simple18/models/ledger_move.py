from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Referencia", readonly=True, default=lambda self: _("New"))
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="cascade")
    type = fields.Selection([
        ("ajuste", "Ajuste"),
        ("pago", "Pago"),
        ("cargo", "Cargo"),
    ], string="Tipo", required=True, default="ajuste")
    direction = fields.Selection([("in", "Entrada"), ("out", "Salida")], string="Dirección", required=True, default="in")
    amount = fields.Monetary(string="Monto", required=True)
    currency_id = fields.Many2one("res.currency", string="Moneda",
                                  related="employee_id.company_id.currency_id", store=True, readonly=True)
    concept = fields.Text(string="Concepto")
    company_id = fields.Many2one("res.company", string="Compañía",
                                 related="employee_id.company_id", store=True, readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get("name") or vals.get("name") == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        return super().create(vals)

    def action_print_receipt(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action")
        return action.report_action(self)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Movimientos", compute="_compute_ledger_data", store=False)
    ledger_balance = fields.Monetary(string="Saldo", compute="_compute_ledger_data",
                                     currency_field="ledger_currency_id", store=False, readonly=True)
    ledger_currency_id = fields.Many2one("res.currency", string="Moneda",
                                         related="company_id.currency_id", store=True, readonly=True)

    def _compute_ledger_data(self):
        for emp in self:
            moves = emp.ledger_move_ids
            emp.ledger_move_count = len(moves)
            balance = 0.0
            for m in moves:
                balance += m.amount if m.direction == "in" else -m.amount
            emp.ledger_balance = balance
