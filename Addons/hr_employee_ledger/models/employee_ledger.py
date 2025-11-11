# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class HrEmployeeLedgerMove(models.Model):
    _name = "hr.employee.ledger.move"
    _description = "Employee Ledger Move (Asiento RRHH)"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Número", readonly=True, copy=False, default="New")
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True, index=True)
    company_id = fields.Many2one("res.company", string="Compañía", required=True, default=lambda self: self.env.company)
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one("account.journal", string="Diario", required=True,
                                 domain=[("type", "in", ("general", "cash", "bank"))])
    currency_id = fields.Many2one("res.currency", string="Moneda", required=True,
                                  default=lambda self: self.env.company.currency_id)
    narration = fields.Text(string="Notas")
    payment_type = fields.Selection([('a','Pago A (dinero)'),('b','Pago B (alimentos)')], string='Tipo de pago', required=True, default='a')
        state = fields.Selection([("draft", "Borrador"),
                              ("posted", "Asentado"),
                              ("cancel", "Cancelado")],
                             default="draft", tracking=True, string="Estado")
    line_ids = fields.One2many("hr.employee.ledger.move.line", "move_id", string="Líneas", copy=True)

    amount_debit = fields.Monetary(string="Débitos", currency_field="currency_id",
                                   compute="_compute_amounts", store=True)
    amount_credit = fields.Monetary(string="Créditos", currency_field="currency_id",
                                    compute="_compute_amounts", store=True)
    balance = fields.Monetary(string="Balance", currency_field="currency_id",
                              compute="_compute_amounts", store=True)

    post_in_accounting = fields.Boolean(string="Postear a Contabilidad", default=False,
                                        help="Si está habilitado, al asentar se generará un asiento contable (account.move) "
                                             "en el diario indicado con las mismas líneas, sin partner; de este modo no impacta "
                                             "en reportes de proveedores.")
    account_move_id = fields.Many2one("account.move", string="Asiento contable", readonly=True, copy=False)
        batch_account_move_id = fields.Many2one('account.move', string='Asiento mensual', readonly=True, copy=False, help='Asiento agregado generado por el cierre mensual.')
        batch_id = fields.Many2one('hr.employee.ledger.batch', string='Lote mensual', readonly=True, copy=False)

    @api.depends("line_ids.debit", "line_ids.credit", "line_ids.display_type")
    def _compute_amounts(self):
        for move in self:
            debit = credit = 0.0
            for line in move.line_ids:
                if line.display_type:
                    continue
                debit += line.debit
                credit += line.credit
            move.amount_debit = debit
            move.amount_credit = credit
            move.balance = debit - credit

    @api.constrains("line_ids", "state")
    def _check_balanced_on_post(self):
        for move in self:
            if move.state == "posted":
                if not move.line_ids:
                    raise ValidationError(_("No se puede asentar sin líneas."))
                # tolerancia por redondeo
                if abs((move.amount_debit or 0.0) - (move.amount_credit or 0.0)) > (move.currency_id.rounding or 0.01):
                    raise ValidationError(_("El asiento debe estar balanceado (débitos = créditos)."))

    def action_post(self):
        for move in self:
            if move.state != "draft":
                raise UserError(_("Solo se pueden asentar movimientos en borrador."))
            if not move.line_ids:
                raise UserError(_("Debe agregar líneas antes de asentar."))
            # Asignar secuencia
            if move.name in (False, "New"):
                seq = self.env.ref("hr_employee_ledger.seq_hr_employee_ledger_move", raise_if_not_found=False)
                move.name = seq.next_by_id() if seq else self.env["ir.sequence"].next_by_code("hr.employee.ledger.move") or "/"
            # Validación de balance
            move._check_balanced_on_post()
            # Crear asiento contable opcional
            if move.post_in_accounting:
                account_move = move._create_account_move()
                account_move.action_post()
                move.account_move_id = account_move.id
            move.state = "posted"
        return True

    def _create_account_move(self):
        self.ensure_one()
        line_vals = []
        for l in self.line_ids:
            if l.display_type:
                continue
            lv = {
                "name": l.name or self.name,
                "account_id": l.account_id.id,
                "debit": l.debit,
                "credit": l.credit,
                "analytic_account_id": l.analytic_account_id.id if l.analytic_account_id else False,
                "analytic_tag_ids": [(6, 0, l.analytic_tag_ids.ids)] if l.analytic_tag_ids else False,
                "company_id": self.company_id.id,
            }
            # No partner para no contaminar reportes de terceros
            line_vals.append((0, 0, lv))
        vals = {
            "date": self.date,
            "journal_id": self.journal_id.id,
            "ref": f"{self.name} - {self.employee_id.name}",
            "line_ids": line_vals,
            "company_id": self.company_id.id,
            "move_type": "entry",
        }
        return self.env["account.move"].create(vals)

    def action_set_to_draft(self):
        for move in self:
            if move.state != "cancel":
                raise UserError(_("Solo puede volver a borrador un movimiento cancelado."))
            move.state = "draft"
        return True

    def action_cancel(self):
        for move in self:
            if move.account_move_id and move.account_move_id.state == "posted":
                raise UserError(_("El asiento contable asociado está posteado. Anúlelo en Contabilidad primero o quite 'Postear a Contabilidad' antes de asentar."))
            move.state = "cancel"
        return True


class HrEmployeeLedgerMoveLine(models.Model):
    _name = "hr.employee.ledger.move.line"
    _description = "Employee Ledger Move Line"
    _order = "sequence, id"

    move_id = fields.Many2one("hr.employee.ledger.move", string="Movimiento", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Descripción", required=True)
    display_type = fields.Selection([("line_section", "Sección"), ("line_note", "Nota")], default=False, help="Campos no contables para secciones/notas.")
    account_id = fields.Many2one("account.account", string="Cuenta contable", required=False,
                                 domain=[("deprecated", "=", False)], help="Si 'Postear a Contabilidad' está activo, se usará esta cuenta.")
    debit = fields.Monetary(string="Débito", currency_field="currency_id", default=0.0)
    credit = fields.Monetary(string="Crédito", currency_field="currency_id", default=0.0)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cuenta analítica")
    analytic_tag_ids = fields.Many2many("account.analytic.tag", string="Etiquetas analíticas")
    currency_id = fields.Many2one(related="move_id.currency_id", store=True, readonly=True)
    employee_id = fields.Many2one(related="move_id.employee_id", store=True, readonly=True)
    company_id = fields.Many2one(related="move_id.company_id", store=True, readonly=True)

    @api.constrains("debit", "credit", "display_type")
    def _check_amounts(self):
        for line in self:
            if line.display_type:
                continue
            if line.debit and line.credit:
                raise ValidationError(_("Una línea no puede tener débito y crédito a la vez."))
            if line.debit < 0.0 or line.credit < 0.0:
                raise ValidationError(_("No se permiten importes negativos."))


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ledger_balance = fields.Monetary(string="Saldo CC Empleado",
                                     currency_field="company_id.currency_id",
                                     compute="_compute_ledger_balance", store=False)
    ledger_move_count = fields.Integer(string="Movimientos CC", compute="_compute_ledger_balance", store=False)

    def _compute_ledger_balance(self):
        Move = self.env["hr.employee.ledger.move"]
        for emp in self:
            moves = Move.search([("employee_id", "=", emp.id), ("state", "=", "posted")])
            debit = sum(m.amount_debit for m in moves)
            credit = sum(m.amount_credit for m in moves)
            emp.ledger_balance = debit - credit
            emp.ledger_move_count = len(moves)

    def action_view_employee_ledger(self):
        self.ensure_one()
        action = self.env.ref("hr_employee_ledger.action_hr_employee_ledger_move").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {
            "default_employee_id": self.id,
            "search_default_employee_id": self.id,
        }
        return action