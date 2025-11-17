# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployeeLedgerBatchWizard(models.TransientModel):
    _name = "hr.employee.ledger.batch.wizard"
    _description = "Cierre mensual de anticipos (A/B) - Preparar lote editable"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    date_from = fields.Date(string="Desde", required=True, default=lambda self: fields.Date.to_date(fields.Date.context_today(self)).replace(day=1))
    date_to = fields.Date(string="Hasta", required=True, default=fields.Date.context_today)
    payment_type = fields.Selection([("a","Pago A (dinero)"),("b","Pago B (alimentos)")], required=True, default="a", string="Tipo")

    include_drafts = fields.Boolean(string="Incluir borradores", default=True)
    confirm_drafts = fields.Boolean(string="Confirmar borradores al generar", default=True)

    journal_id = fields.Many2one("account.journal", string="Diario contable", domain=[("type","in",("general","cash","bank"))])
    memo = fields.Char(string="Referencia", default=lambda self: _("Cierre anticipos RRHH"))

    def action_generate(self):
        self.ensure_one()
        company = self.company_id
        journal = self.journal_id or company.employee_batch_journal_id
        if not journal:
            raise UserError(_("Defina un Diario en Compañía (pestaña RRHH - Anticipos) o en el asistente."))

        advance_account = company.employee_advance_account_a_id if self.payment_type == "a" else company.employee_advance_account_b_id
        if not advance_account:
            raise UserError(_("Defina la cuenta de anticipos para el tipo %s en Compañía.") % (self.payment_type.upper()))

        Move = self.env["hr.employee.ledger.move"]
        domain = [
            ("company_id","=",company.id),
            ("payment_type","=", self.payment_type),
            ("date",">=", self.date_from),
            ("date","<=", self.date_to),
            ("batch_id","=", False),
            ("state","in", ["posted","draft"] if self.include_drafts else ["posted"]),
        ]
        moves = Move.search(domain, order="date asc, id asc")
        if not moves:
            raise UserError(_("No hay movimientos elegibles para el período seleccionado."))

        if self.confirm_drafts:
            drafts = moves.filtered(lambda m: m.state == "draft")
            if drafts:
                drafts.action_post()

        totals_by_account = {}
        for m in moves:
            acc = m.account_src_id
            if not acc:
                continue
            totals_by_account.setdefault(acc.id, {"account": acc, "amount": 0.0})
            totals_by_account[acc.id]["amount"] += (m.amount or 0.0)

        batch = self.env["hr.employee.ledger.batch"].create({
            "company_id": company.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "payment_type": self.payment_type,
            "journal_id": journal.id,
            "debit_account_id": advance_account.id,
            "memo": self.memo,
        })

        credit_lines = []
        for d in totals_by_account.values():
            credit_lines.append((0,0,{
                "sequence": 10,
                "name": "Salida %s" % (d["account"].name),
                "account_id": d["account"].id,
                "amount": d["amount"],
            }))
        if credit_lines:
            batch.write({"credit_line_ids": credit_lines})

        emp_map = {}
        for m in moves:
            emp = m.employee_id
            emp_map.setdefault(emp.id, {"employee": emp, "amount": 0.0, "count": 0})
            emp_map[emp.id]["amount"] += (m.amount or 0.0)
            emp_map[emp.id]["count"] += 1
        emp_lines = []
        for e in emp_map.values():
            emp_lines.append((0,0,{
                "employee_id": e["employee"].id,
                "amount": e["amount"],
                "count_moves": e["count"],
            }))
        if emp_lines:
            batch.write({"employee_line_ids": emp_lines})

        moves.write({"batch_id": batch.id})

        seq = self.env.ref("hr_employee_ledger.seq_hr_employee_ledger_batch", raise_if_not_found=False)
        name = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.batch") or "/"
        batch.name = name

        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.employee.ledger.batch",
            "view_mode": "form",
            "res_id": batch.id,
            "target": "current",
        }
