from odoo import api, fields, models, _

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Movimiento de cuenta corriente de empleado"
    _order = "date desc, id desc"

    name = fields.Char(string="Referencia", default="/", readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda self: self.env.company, index=True)
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today, index=True)
    concept = fields.Char(string="Concepto", required=True)
    move_kind = fields.Selection([
        ("A", "Anticipo (Dinero)"),
        ("B", "Alimentos"),
    ], string="Tipo", required=True, default="A", help="A = anticipo de dinero, B = alimentos")
    direction = fields.Selection([
        ("debit", "Cargo"),
        ("credit", "Abono (Devolución / Descuento)")
    ], string="Dirección", required=True, default="debit")
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True, default=lambda self: self.env.company.currency_id.id)
    amount = fields.Monetary(string="Importe", required=True, currency_field="currency_id")
    amount_signed = fields.Monetary(string="Importe (signado)", compute="_compute_amount_signed", currency_field="currency_id", store=False)
    note = fields.Text(string="Notas")

    @api.depends("amount", "direction")
    def _compute_amount_signed(self):
        for rec in self:
            rec.amount_signed = rec.amount if rec.direction == "debit" else -rec.amount

    def _next_sequence(self):
        return self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
        return super().create(vals_list)