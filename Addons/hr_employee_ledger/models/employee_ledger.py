# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "RRHH - Pseudo movimiento (A/B)"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Número", readonly=True, copy=False, default="New")
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda self: self.env.company)

    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    payment_type = fields.Selection([("a","Pago A (dinero)"),("b","Pago B (alimentos)")], required=True, default="a", string="Tipo de pago")
    account_src_id = fields.Many2one("account.account", string="Cuenta de salida (caja/banco)", required=True, domain=[("deprecated","=",False)])
    amount = fields.Monetary(string="Importe", required=False, default=0.0, currency_field="currency_id")
    concept = fields.Char(string="Concepto abonado", required=False)
    narration = fields.Text(string="Notas")
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True, default=lambda self: self.env.company.currency_id)

    state = fields.Selection([("draft","Borrador"),("posted","Asentado"),("cancel","Cancelado")], default="draft", string="Estado")

    account_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True, copy=False)
    batch_account_move_id = fields.Many2one("account.move", string="Asiento mensual", readonly=True, copy=False)
    batch_id = fields.Many2one("hr.employee.ledger.batch", string="Lote mensual", readonly=True, copy=False)

    amount_debit = fields.Monetary(string="Débitos", currency_field="currency_id", compute="_compute_amounts", store=False)
    amount_credit = fields.Monetary(string="Créditos", currency_field="currency_id", compute="_compute_amounts", store=False)
    balance = fields.Monetary(string="Balance", currency_field="currency_id", compute="_compute_amounts", store=False)

    @api.depends("amount")
    def _compute_amounts(self):
        for move in self:
            amt = move.amount or 0.0
            move.amount_debit = amt
            move.amount_credit = 0.0
            move.balance = amt

    @api.constrains("amount")
    def _check_amount(self):
        for move in self:
            if (move.amount or 0.0) <= 0.0:
                raise ValidationError(_("El importe debe ser mayor a 0."))

    def action_post(self):
        for move in self:
            if move.state != "draft":
                raise UserError(_("Solo se pueden asentar movimientos en borrador."))
            if not move.account_src_id:
                raise UserError(_("Debe indicar la cuenta de salida."))
            if not move.amount or move.amount <= 0:
                raise UserError(_("Debe indicar un importe mayor a 0."))
            if move.name in (False, "New"):
                seq = self.env.ref("hr_employee_ledger.seq_hr_employee_ledger_move", raise_if_not_found=False)
                move.name = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
            move.state = "posted"
        return True

    def action_set_to_draft(self):
        for move in self:
            if move.state != "cancel":
                raise UserError(_("Solo puede volver a borrador un movimiento cancelado."))
            move.state = "draft"
        return True

    def action_cancel(self):
        for move in self:
            if move.account_move_id and move.account_move_id.state == "posted":
                raise UserError(_("El asiento contable asociado está posteado. Anúlelo en Contabilidad antes de cancelar."))
            move.state = "cancel"
        return True

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref('hr_employee_ledger.action_report_employee_payment_receipt').report_action(self)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, string='Moneda compañía')
    ledger_balance = fields.Monetary(string="Saldo CC Empleado", currency_field="company_currency_id", compute="_compute_ledger_balance", store=False)
    ledger_move_count = fields.Integer(string="Movimientos CC", compute="_compute_ledger_balance", store=False)

    def _compute_ledger_balance(self):
        Move = self.env["hr.employee.ledger.move"]
        for emp in self:
            moves = Move.search([("employee_id","=", emp.id), ("state","=","posted")])
            emp.ledger_balance = sum(m.amount for m in moves)
            emp.ledger_move_count = len(moves)

    def action_view_employee_ledger(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger.action_hr_employee_ledger_move").read()[0]
        action["domain"] = [("employee_id","=", self.id)]
        action["context"] = {"default_employee_id": self.id, "search_default_employee_id": self.id}
        return action