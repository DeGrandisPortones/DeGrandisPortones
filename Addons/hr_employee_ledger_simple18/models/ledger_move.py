
from odoo import api, fields, models, _

class EmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"

    name = fields.Char(string="Número", default=lambda self: _("New"), readonly=True, copy=False)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True, index=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True, ondelete="cascade")
    type = fields.Selection([
        ("manual","Manual"),
        ("payment","Pago"),
        ("advance","Adelanto"),
        ("adjustment","Ajuste"),
    ], string="Tipo", required=True, default="manual")
    direction = fields.Selection([("in","Entrada (+)"),("out","Salida (-)")], string="Dirección", required=True, default="out")
    concept = fields.Char(string="Concepto")
    amount = fields.Monetary(string="Monto", required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("name") in (False, _("New")):
                if seq:
                    vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or _("New")
                else:
                    vals["name"] = _("New")
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        # QWeb report action
        return self.env.ref("hr_employee_ledger_simple18.employee_ledger_move_receipt_action").report_action(self)
