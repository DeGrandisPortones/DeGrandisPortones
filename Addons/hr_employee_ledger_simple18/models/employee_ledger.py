from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move"
    _order = "date desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Número", default="/", copy=False)
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True, ondelete="cascade")
    move_type = fields.Selection([
        ("A", "Anticipo de dinero (A)"),
        ("B", "Alimentos (B)"),
    ], string="Tipo", required=True, default="A")
    direction = fields.Selection([
        ("out", "Pago al empleado (sale de la empresa)"),
        ("in", "Devolución/Descuento (vuelve a la empresa)"),
    ], string="Dirección", required=True, default="out")
    amount = fields.Monetary(string="Importe", required=True, default=0.0, currency_field="currency_id")
    concept = fields.Char(string="Concepto", required=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one("res.company", string="Compañía", related="employee_id.company_id", store=True, readonly=True)

    # Campos auxiliares
    signed_amount = fields.Monetary(string="Importe firmado", compute="_compute_signed_amount", store=True, currency_field="currency_id")

    @api.depends("amount", "direction")
    def _compute_signed_amount(self):
        for rec in self:
            sign = -1 if rec.direction == "out" else 1
            rec.signed_amount = (rec.amount or 0.0) * sign

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env.ref("hr_employee_ledger_simple18.seq_hr_employee_ledger_move", raise_if_not_found=False)
        for vals in vals_list:
            if vals.get("name", "/") in ("/", False) and seq:
                vals["name"] = seq.next_by_id()
        return super().create(vals_list)

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("hr_employee_ledger_simple18.action_report_employee_move_receipt").report_action(self)

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_move_ids = fields.One2many("hr.employee.ledger.move", "employee_id", string="Movimientos")
    ledger_move_count = fields.Integer(string="Nº Movimientos", compute="_compute_ledger_move_count")
    ledger_balance = fields.Monetary(string="Saldo Cuenta Corriente", compute="_compute_ledger_balance", currency_field="company_currency_id", store=False)
    company_currency_id = fields.Many2one("res.currency", string="Moneda compañía", related="company_id.currency_id", readonly=True)

    @api.depends("ledger_move_ids")
    def _compute_ledger_move_count(self):
        for emp in self:
            emp.ledger_move_count = len(emp.ledger_move_ids)

    def _compute_ledger_balance(self):
        for emp in self:
            # sumatoria de signed_amount
            total = 0.0
            for mv in emp.ledger_move_ids:
                total += mv.signed_amount or 0.0
            emp.ledger_balance = total

    def action_open_ledger_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos de %s") % (self.name,),
            "res_model": "hr.employee.ledger.move",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }