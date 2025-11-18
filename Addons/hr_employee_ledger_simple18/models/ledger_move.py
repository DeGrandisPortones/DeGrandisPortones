from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Reference", readonly=True, default="/")
    date = fields.Date(default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, ondelete="cascade")
    type = fields.Selection([("payment","Pago"),("charge","Cargo")], required=True, default="payment")
    direction = fields.Selection([("in","Crédito"),("out","Débito")], required=True, default="in")
    amount = fields.Monetary(string="Amount", required=True)
    concept = fields.Char(string="Concepto")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", readonly=True, store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        # action defined in report/report_actions.xml
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)