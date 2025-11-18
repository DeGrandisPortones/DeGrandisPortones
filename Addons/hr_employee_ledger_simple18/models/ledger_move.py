
from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    type = fields.Selection([("abono", "Abono"), ("cargo", "Cargo")], required=True, default="abono")
    direction = fields.Selection([("in", "Entrada"), ("out", "Salida")], required=True, default="in")
    concept = fields.Char()
    amount = fields.Monetary(required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id, required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) in (False, _("New")):
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or _("New")
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)
