from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Number", default="New", readonly=True, copy=False)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, ondelete="restrict")
    type = fields.Selection([
        ("credit", "Credit"),
        ("debit", "Debit"),
    ], string="Type", required=True, default="credit")
    direction = fields.Selection([
        ("in", "In"),
        ("out", "Out"),
    ], string="Direction", required=True, default="in")
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one("res.currency", string="Currency",
                                  default=lambda self: self.env.company.currency_id.id, required=True)
    concept = fields.Text(string="Concept")

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                nextval = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") if not seq else seq.next_by_id()
                vals["name"] = nextval or "/"
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)