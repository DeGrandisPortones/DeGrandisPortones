from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Referencia", readonly=True, copy=False, default="/")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, ondelete="cascade", index=True)
    type = fields.Selection(
        [
            ("abono", "Abono"),
            ("cargo", "Cargo"),
        ],
        string="Tipo",
        required=True,
        default="abono",
    )
    direction = fields.Selection(
        [
            ("in", "Entrada"),
            ("out", "Salida"),
        ],
        string="Dirección",
        required=True,
        default="in",
    )
    concept = fields.Char(string="Concepto")
    amount = fields.Monetary(string="Importe", required=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="employee_id.company_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)