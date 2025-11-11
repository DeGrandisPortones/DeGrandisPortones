# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrEmployeeLedgerBatch(models.Model):
    _name = "hr.employee.ledger.batch"
    _description = "Cierre mensual de anticipos RRHH (editable)"
    _order = "date_to desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Número", readonly=True, copy=False, default="New")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    date_from = fields.Date(string="Desde", required=True)
    date_to = fields.Date(string="Hasta", required=True)
    payment_type = fields.Selection([("a","Pago A (dinero)"),("b","Pago B (alimentos)")], required=True, default="a", string="Tipo")

    journal_id = fields.Many2one("account.journal", string="Diario contable", required=True, domain=[("type","in",("general","cash","bank"))])
    debit_account_id = fields.Many2one("account.account", string="Cuenta débito (Anticipos)", required=True, domain=[("deprecated","=",False)])

    memo = fields.Char(string="Referencia", default=lambda self: _("Cierre anticipos RRHH"))
    state = fields.Selection([("draft","Borrador"),("posted","Asentado"),("cancel","Cancelado")], default="draft", string="Estado")
    account_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True, copy=False)

    # Movimientos de RRHH incluidos en este lote
    move_ids = fields.One2many("hr.employee.ledger.move", "batch_id", string="Movimientos")
    move_total_amount = fields.Monetary(string="Total movimientos", currency_field="currency_id", compute="_compute_totals", store=False)
    move_count = fields.Integer(string="Cantidad movimientos", compute="_compute_totals", store=False)

    # Líneas de crédito (libres): una por cuenta de salida (Caja/Banco u otras)
    credit_line_ids = fields.One2many("hr.employee.ledger.batch.credit.line", "batch_id", string="Contrapartidas (Crédito)", copy=True)
    credit_total_amount = fields.Monetary(string="Total crédito", currency_field="currency_id", compute="_compute_credit_total", store=False)
        difference_amount = fields.Monetary(string="Diferencia", currency_field="currency_id", compute="_compute_credit_total", store=False)

    # Resumen por empleado (solo trazabilidad interna)
    employee_line_ids = fields.One2many("hr.employee.ledger.batch.employee.line", "batch_id", string="Detalle por empleado", copy=True)

    @api.depends("move_ids.amount_debit", "move_ids.amount_credit")
    def _compute_totals(self):
        for batch in self:
            total = 0.0
            for m in batch.move_ids:
                # movimientos balanceados: usamos el total de débito
                total += m.amount_debit
            batch.move_total_amount = total
            batch.move_count = len(batch.move_ids)

    @api.depends("credit_line_ids.amount")
    def _compute_credit_total(self):
        for batch in self:
            batch.credit_total_amount = sum(l.amount for l in batch.credit_line_ids)

    def action_post(self):
        for batch in self:
            if batch.state != "draft":
                raise UserError(_("Solo se pueden asentar lotes en borrador."))
            if not batch.move_ids:
                raise UserError(_("No hay movimientos en el lote."))
            # Validar balance: total créditos = total movimientos
            rounding = batch.currency_id.rounding or 0.01
            if abs((batch.credit_total_amount or 0.0) - (batch.move_total_amount or 0.0)) > rounding:
                raise ValidationError(_("El total de créditos (%s) debe igualar el total de movimientos (%s).") % (batch.credit_total_amount, batch.move_total_amount))

            # Construir asiento contable
            line_vals = []
            # Débito a anticipos
            line_vals.append((0,0,{
                "name": "%s %s" % (batch.memo or "", batch.payment_type.upper()),
                "account_id": batch.debit_account_id.id,
                "debit": batch.move_total_amount,
                "credit": 0.0,
                "company_id": batch.company_id.id,
            }))
            # Créditos libres
            for cl in batch.credit_line_ids:
                if not cl.account_id or cl.amount <= 0.0:
                    continue
                line_vals.append((0,0,{
                    "name": cl.name or ("Anticipos %s" % (batch.payment_type.upper())),
                    "account_id": cl.account_id.id,
                    "debit": 0.0,
                    "credit": cl.amount,
                    "company_id": batch.company_id.id,
                }))

            acc_move = self.env["account.move"].create({
                "date": batch.date_to,
                "journal_id": batch.journal_id.id,
                "ref": "%s %s [%s - %s]" % (batch.memo or "", batch.payment_type.upper(), batch.date_from, batch.date_to),
                "line_ids": line_vals,
                "company_id": batch.company_id.id,
                "move_type": "entry",
            })
            acc_move.action_post()
            batch.account_move_id = acc_move.id
            # vincular movimientos
            batch.move_ids.write({"batch_account_move_id": acc_move.id})
            batch.state = "posted"
        return True

    def action_cancel(self):
        for batch in self:
            if batch.account_move_id and batch.account_move_id.state == "posted":
                raise UserError(_("El asiento contable está posteado. Anúlelo desde Contabilidad antes de cancelar el lote."))
            batch.state = "cancel"
        return True

    def action_open_moves(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger.action_hr_employee_ledger_move").read()[0]
        action["domain"] = [("batch_id","=", self.id)]
        action["context"] = {"default_batch_id": self.id}
        return action


class HrEmployeeLedgerBatchCreditLine(models.Model):
    _name = "hr.employee.ledger.batch.credit.line"
    _description = "Línea de crédito lote RRHH"
    _order = "sequence, id"

    batch_id = fields.Many2one("hr.employee.ledger.batch", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Etiqueta")
    account_id = fields.Many2one("account.account", string="Cuenta crédito", required=True, domain=[("deprecated","=",False)])
    amount = fields.Monetary(string="Importe crédito", required=True, default=0.0, currency_field="currency_id")
    currency_id = fields.Many2one(related="batch_id.currency_id", store=True, readonly=True)


class HrEmployeeLedgerBatchEmployeeLine(models.Model):
    _name = "hr.employee.ledger.batch.employee.line"
    _description = "Detalle por empleado - lote RRHH"
    _order = "employee_id"

    batch_id = fields.Many2one("hr.employee.ledger.batch", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", required=True)
    amount = fields.Monetary(string="Importe total", currency_field="currency_id")
    count_moves = fields.Integer(string="Movimientos")
    currency_id = fields.Many2one(related="batch_id.currency_id", store=True, readonly=True)