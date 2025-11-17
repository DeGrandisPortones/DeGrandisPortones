
# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrEmployeeLedgerBatch(models.Model):
    _name = "hr.employee.ledger.batch"
    _description = "Cierre de anticipos RRHH (editable)"
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(string="Número", readonly=True, copy=False, default="New")
    company_id = fields.Many2one("res.company", required=True, default=lambda s: s.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    date_from = fields.Date(string="Desde", required=True)
    date_to = fields.Date(string="Hasta", required=True)
    payment_type = fields.Selection([("a","Pago A (dinero)"),("b","Pago B (alimentos)")], required=True, default="a", string="Tipo")

    journal_id = fields.Many2one("account.journal", string="Diario contable", required=True, domain=[("type","in",("general","cash","bank"))])
    debit_account_id = fields.Many2one("account.account", string="Cuenta débito (Anticipos)", required=True, domain=[("deprecated","=",False)])

    memo = fields.Char(string="Referencia", default=lambda s: _("Cierre anticipos RRHH"))
    state = fields.Selection([("draft","Borrador"),("posted","Asentado"),("cancel","Cancelado")], default="draft", string="Estado")
    account_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True, copy=False)

    move_ids = fields.One2many("hr.employee.ledger.move", "batch_id", string="Movimientos")
    move_total_amount = fields.Monetary(string="Total movimientos", currency_field="currency_id", compute="_compute_totals")
    move_count = fields.Integer(string="Cantidad movimientos", compute="_compute_totals")

    credit_line_ids = fields.One2many("hr.employee.ledger.batch.credit.line", "batch_id", string="Contrapartidas (Crédito)", copy=True)
    credit_total_amount = fields.Monetary(string="Total crédito", currency_field="currency_id", compute="_compute_credit_total")
    difference_amount = fields.Monetary(string="Diferencia", currency_field="currency_id", compute="_compute_credit_total")

    employee_line_ids = fields.One2many("hr.employee.ledger.batch.employee.line", "batch_id", string="Detalle por empleado", copy=True)

    @api.depends("move_ids.amount")
    def _compute_totals(self):
        for b in self:
            b.move_total_amount = sum(m.amount for m in b.move_ids)
            b.move_count = len(b.move_ids)

    @api.depends("credit_line_ids.amount")
    def _compute_credit_total(self):
        for b in self:
            b.credit_total_amount = sum(l.amount for l in b.credit_line_ids)
            b.difference_amount = (b.move_total_amount or 0.0) - (b.credit_total_amount or 0.0)

    def action_post(self):
        for b in self:
            if b.state != "draft":
                raise UserError(_("Solo se pueden asentar lotes en borrador."))
            if not b.move_ids:
                raise UserError(_("No hay movimientos en el lote."))
            rounding = b.currency_id.rounding or 0.01
            if abs((b.credit_total_amount or 0.0) - (b.move_total_amount or 0.0)) > rounding:
                raise ValidationError(_("El total de créditos (%s) debe igualar el total de movimientos (%s).") % (b.credit_total_amount, b.move_total_amount))

            lines = [(0,0,{"name": "%s %s" % (b.memo or "", b.payment_type.upper()), "account_id": b.debit_account_id.id, "debit": b.move_total_amount, "credit": 0.0, "company_id": b.company_id.id})]
            for cl in b.credit_line_ids:
                if cl.account_id and cl.amount > 0:
                    lines.append((0,0,{"name": cl.name or ("Anticipos %s" % b.payment_type.upper()), "account_id": cl.account_id.id, "debit": 0.0, "credit": cl.amount, "company_id": b.company_id.id}))
            am = self.env["account.move"].create({"date": b.date_to, "journal_id": b.journal_id.id, "ref": "%s %s [%s - %s]" % (b.memo or "", b.payment_type.upper(), b.date_from, b.date_to), "line_ids": lines, "company_id": b.company_id.id, "move_type": "entry"})
            am.action_post()
            b.account_move_id = am.id
            b.move_ids.write({"batch_account_move_id": am.id})
            b.state = "posted"
        return True

    @api.model
    def _create_single_batch_from_moves(self, company, payment_type, moves):
        if not moves:
            return False
        journal = company.employee_batch_journal_id
        debit_account = company.employee_advance_account_a_id if payment_type == "a" else company.employee_advance_account_b_id

        dates = [m.date for m in moves if m.date]
        date_from = min(dates) if dates else fields.Date.context_today(self)
        date_to = max(dates) if dates else fields.Date.context_today(self)

        totals_by_account = defaultdict(float)
        for m in moves:
            if m.account_src_id:
                totals_by_account[m.account_src_id.id] += (m.amount or 0.0)

        batch = self.create({"company_id": company.id, "date_from": date_from, "date_to": date_to, "payment_type": payment_type, "journal_id": journal.id, "debit_account_id": debit_account.id, "memo": _("Cierre anticipos RRHH")})

        credit_lines = []
        Account = self.env["account.account"].browse
        for acc_id, amt in totals_by_account.items():
            credit_lines.append((0,0,{"sequence": 10, "name": _("Salida %s") % Account(acc_id).name, "account_id": acc_id, "amount": amt}))
        if credit_lines:
            batch.write({"credit_line_ids": credit_lines})

        emp_map = defaultdict(lambda: {"amount": 0.0, "count": 0})
        for m in moves:
            emp_map[m.employee_id.id]["amount"] += (m.amount or 0.0)
            emp_map[m.employee_id.id]["count"] += 1
        emp_lines = [(0,0,{"employee_id": eid, "amount": d["amount"], "count_moves": d["count"]}) for eid, d in emp_map.items()]
        if emp_lines:
            batch.write({"employee_line_ids": emp_lines})

        moves.write({"batch_id": batch.id})

        seq = self.env.ref("hr_employee_ledger.seq_hr_employee_ledger_batch", raise_if_not_found=False)
        batch.name = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.batch") or "/"
        return batch


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
