
from odoo import models, fields, api, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default="/", required=True, readonly=True)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    type = fields.Selection([
        ("payment", "Pago"),
        ("charge", "Cargo"),
    ], string="Tipo", required=True, default="payment")
    direction = fields.Selection([("in", "Entrada"), ("out", "Salida")], string="Dirección", required=True, default="in")
    concept = fields.Char(string="Concepto")
    amount = fields.Monetary(string="Importe", currency_field="currency_id", required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", string="Moneda", default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda self: self.env.company.id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move")
                vals["name"] = self.env['ir.sequence'].next_by_code(seq.code)
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)
