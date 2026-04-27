from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheck(models.Model):
    _name = "dflex.check"
    _description = "Cheque propio"
    _order = "number asc, id asc"
    _rec_name = "name"

    # Datos principales
    name = fields.Char(string="N° Cheque", required=True, index=True, copy=False)
    number = fields.Integer(string="Número", required=True, index=True)
    checkbook_id = fields.Many2one("dflex.checkbook", string="Chequera", ondelete="restrict")
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario banco",
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        check_company=True,
        index=True,
        help="Diario/banco desde el que se emite el cheque propio.",
    )
    bank_id = fields.Many2one(
        "res.bank",
        string="Banco",
        compute="_compute_bank_id",
        store=True,
        readonly=False,
        help="Banco asociado al diario. Se conserva por compatibilidad con cheques existentes.",
    )
    type = fields.Selection(
        [("fisico", "Físico"), ("echeq", "eCheq")],
        string="Tipo de cheque",
        required=True,
        default="fisico",
        help="Indica si el cheque propio es físico o electrónico.",
    )

    # Fechas e importes
    issue_date = fields.Date(string="Fecha Emisión")
    payment_date = fields.Date(string="Fecha de pago")
    delivery_date = fields.Date(
        string="Fecha entrega",
        readonly=True,
        copy=False,
        help="Fecha en la que el cheque propio se entregó mediante un pago.",
    )
    amount = fields.Monetary(string="Importe")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)

    # Proveedor / destinatario
    partner_id = fields.Many2one("res.partner", string="Entregado a")
    cuit_proveedor = fields.Char(string="CUIT Proveedor", related="partner_id.vat", store=True)
    partner_name = fields.Char(string="Razón Social Proveedor", related="partner_id.name", store=True)

    # Estado del ciclo del cheque
    state = fields.Selection(
        [
            ("available", "En Cartera"),
            ("delivered", "Entregado"),
            ("pending_entry", "Por ingresar"),
            ("expired", "Vencido"),
            ("debited", "Pagado"),
            ("returned", "Devuelto"),
            ("cancelled", "Anulado"),
        ],
        string="Estado",
        default="available",
        index=True,
    )

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company, required=True
    )

    # Auditoría
    move_id = fields.Many2one("account.move", string="Asiento relacionado", readonly=True)
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago relacionado",
        readonly=True,
        copy=False,
        help="Pago en el que este cheque fue utilizado/entregado.",
    )
    payment_line_id = fields.Many2one(
        "dflex.payment.check.line",
        string="Línea de pago relacionada",
        readonly=True,
        copy=False,
    )
    note = fields.Text(string="Notas")

    _sql_constraints = [
        (
            "unique_check_per_journal_company",
            "unique(number, journal_id, company_id)",
            "Ya existe un cheque con ese número para este diario y compañía.",
        )
    ]

    @api.depends("journal_id", "journal_id.bank_id")
    def _compute_bank_id(self):
        for rec in self:
            if rec.journal_id and "bank_id" in rec.journal_id._fields:
                rec.bank_id = rec.journal_id.bank_id

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        for rec in self:
            if rec.journal_id and "bank_id" in rec.journal_id._fields:
                rec.bank_id = rec.journal_id.bank_id

    def _get_available_action(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Cheques propios en cartera"),
            "res_model": "dflex.check",
            "view_mode": "list,form",
            "domain": [("state", "=", "available")],
            "context": {"search_default_available": 1},
        }

    def _is_payment_reconciled_in_bank(self):
        self.ensure_one()
        payment = self.payment_id
        if not payment or not payment.move_id:
            return False

        move = payment.move_id

        # IMPORTANT: account.payment.state == "paid" only means that the payment
        # was posted/validated. It does NOT mean that the check was debited by
        # the bank. A check must move to Pagado only when the liquidity/outstanding
        # line is reconciled through a bank statement/reconciliation move.
        liquidity_lines = move.line_ids.filtered(lambda line: line.account_id.account_type == "asset_cash")
        if not liquidity_lines:
            liquidity_lines = move.line_ids.filtered(lambda line: line.journal_id.type in ["bank", "cash"])

        for line in liquidity_lines:
            if "statement_line_id" in line._fields and line.statement_line_id:
                return True

            matched_lines = self.env["account.move.line"]
            if "matched_debit_ids" in line._fields:
                matched_lines |= line.matched_debit_ids.mapped("debit_move_id")
                matched_lines |= line.matched_debit_ids.mapped("credit_move_id")
            if "matched_credit_ids" in line._fields:
                matched_lines |= line.matched_credit_ids.mapped("debit_move_id")
                matched_lines |= line.matched_credit_ids.mapped("credit_move_id")

            matched_lines -= line
            for matched_line in matched_lines:
                if "statement_line_id" in matched_line._fields and matched_line.statement_line_id:
                    return True
                if "statement_line_id" in matched_line.move_id._fields and matched_line.move_id.statement_line_id:
                    return True

        return False

    def _get_state_from_dates_and_payment(self):
        self.ensure_one()
        if self.state in ["available", "returned", "cancelled"]:
            return self.state

        if self._is_payment_reconciled_in_bank():
            return "debited"

        today = fields.Date.context_today(self)
        if self.payment_date:
            expired_date = self.payment_date + relativedelta(months=1)
            if today >= expired_date:
                return "expired"
            if today >= self.payment_date:
                return "pending_entry"

        return "delivered"

    def _update_operational_state(self):
        for check in self.filtered(lambda c: c.state in ["delivered", "pending_entry", "expired", "debited"]):
            new_state = check._get_state_from_dates_and_payment()
            if new_state != check.state:
                check.state = new_state

    @api.model
    def _cron_update_check_states(self):
        checks = self.search([("state", "in", ["delivered", "pending_entry", "expired", "debited"]), ("payment_id", "!=", False)])
        checks._update_operational_state()
        return True

    def action_update_operational_state(self):
        records = self if self else self.search([("state", "in", ["delivered", "pending_entry", "expired", "debited"]), ("payment_id", "!=", False)])
        records._update_operational_state()
        return True

    # Acciones de estado
    def action_deliver(self):
        for check in self:
            if check.state != "available":
                raise ValidationError(_("Solo se pueden entregar cheques en estado En Cartera."))
            check.state = "delivered"

    def action_pending_entry(self):
        for check in self:
            if check.state != "delivered":
                raise ValidationError(_("Solo se pueden marcar Por ingresar cheques en estado Entregado."))
            check.state = "pending_entry"

    def action_debit(self):
        for check in self:
            if check.state not in ["delivered", "pending_entry", "expired"]:
                raise ValidationError(_("Solo se pueden marcar como Pagados cheques Entregados, Por ingresar o Vencidos."))
            check.state = "debited"

    def action_cancel(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede anular un cheque ya pagado."))
            check.state = "cancelled"

    def action_return(self):
        """Marca el cheque como devuelto/rechazado."""
        for check in self:
            if check.state not in ["delivered", "pending_entry", "expired"]:
                raise ValidationError(_("Solo se pueden marcar como Devueltos cheques Entregados, Por ingresar o Vencidos."))
            check.state = "returned"

    def _clear_payment_usage_values(self):
        return {
            "state": "available",
            "payment_id": False,
            "payment_line_id": False,
            "move_id": False,
            "issue_date": False,
            "payment_date": False,
            "delivery_date": False,
            "amount": 0.0,
            "partner_id": False,
        }

    def action_reset_available(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede volver a En Cartera un cheque ya pagado."))
            check.write(check._clear_payment_usage_values())

    @api.onchange("number")
    def _onchange_number(self):
        for rec in self:
            if rec.number:
                rec.name = str(rec.number)

    @api.model
    def _assign_missing_journals_from_bank(self):
        """Best-effort migration for old records created when the model used res.bank only."""
        checks = self.search([("journal_id", "=", False), ("bank_id", "!=", False)])
        for check in checks:
            journal = self.env["account.journal"].search(
                [
                    ("type", "in", ["bank", "cash"]),
                    ("company_id", "=", check.company_id.id),
                    ("bank_id", "=", check.bank_id.id),
                ],
                limit=1,
            )
            if journal:
                check.journal_id = journal.id
        return True
