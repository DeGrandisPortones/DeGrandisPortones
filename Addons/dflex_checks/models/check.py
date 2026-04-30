from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheck(models.Model):
    _name = "dflex.check"
    _description = "Cheque propio"
    _order = "number asc, id asc"
    _rec_name = "name"

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
    )

    issue_date = fields.Date(string="Fecha emisión")
    payment_date = fields.Date(string="Fecha de pago")
    delivery_date = fields.Date(
        string="Fecha entrega",
        readonly=True,
        copy=False,
        help="Fecha en la que el cheque propio se entregó mediante un pago.",
    )
    amount = fields.Monetary(string="Importe")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)

    partner_id = fields.Many2one("res.partner", string="Entregado a")
    cuit_proveedor = fields.Char(string="CUIT", related="partner_id.vat", store=True)
    partner_name = fields.Char(string="Proveedor", related="partner_id.name", store=True)

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

    move_id = fields.Many2one(
        "account.move",
        string="Asiento pago relacionado",
        readonly=True,
        help="Asiento del pago que entregó el cheque propio contra la cuenta puente.",
    )
    debit_move_id = fields.Many2one(
        "account.move",
        string="Asiento débito banco",
        readonly=True,
        copy=False,
        help="Asiento creado al debitar este cheque propio contra el banco.",
    )
    reversal_move_id = fields.Many2one(
        "account.move",
        string="Asiento anulación/devolución",
        readonly=True,
        copy=False,
        help="Asiento contrario al asiento del pago, creado al anular o devolver este cheque propio.",
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago relacionado",
        readonly=True,
        copy=False,
        help="Pago en el que este cheque fue utilizado/entregado.",
    )
    note = fields.Text(string="Notas")

    _sql_constraints = [
        (
            "unique_check_per_journal_company",
            "unique(number, journal_id, company_id)",
            "Ya existe un cheque con ese número para este diario y compañía.",
        ),
    ]

    def get_view(self, view_id=None, view_type="form", **options):
        """Force amount totals in list views, including Studio/custom inherited views.

        The XML view already has sum="Total", but Studio/custom list variants may
        replace the amount field and remove the aggregate attribute. This keeps the
        footer total visible for the current search/filter, for example Vencidos.
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type not in ("list", "tree") or not res.get("arch"):
            return res

        try:
            arch = etree.fromstring(res["arch"])
        except Exception:
            return res

        changed = False
        for node in arch.xpath("//field[@name='amount']"):
            if node.get("sum") != "Total":
                node.set("sum", "Total")
                changed = True

        if changed:
            res["arch"] = etree.tostring(arch, encoding="unicode")
        return res

    @api.depends("journal_id", "journal_id.bank_id")
    def _compute_bank_id(self):
        for rec in self:
            if rec.journal_id and "bank_id" in rec.journal_id._fields:
                rec.bank_id = rec.journal_id.bank_id
            elif not rec.journal_id:
                rec.bank_id = rec.bank_id

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

        # En el flujo DFlex, cada cheque se debita individualmente.
        # Si ya se creó/posteó el asiento de débito del cheque, el cheque está Pagado.
        if "debit_move_id" in self._fields and self.debit_move_id and self.debit_move_id.state == "posted":
            return True

        payment = self.payment_id
        if not payment or not payment.move_id:
            return False

        move = payment.move_id

        # payment.state == "paid" solo indica que el pago fue validado/conciliado
        # con deuda. No alcanza para marcar cada cheque como Pagado.
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

    def _get_own_check_pending_account(self):
        self.ensure_one()

        if self.payment_id and self.payment_id.payment_method_line_id.payment_account_id:
            return self.payment_id.payment_method_line_id.payment_account_id

        method_lines = self.journal_id.outbound_payment_method_line_ids.filtered(
            lambda line: (
                line.code == "own_checks"
                or line.payment_method_id.code == "own_checks"
                or "cheques propios" in " ".join(part for part in [line.name, line.payment_method_id.name] if part).lower()
                or "own check" in " ".join(part for part in [line.name, line.payment_method_id.name] if part).lower()
            )
        )
        account = method_lines.filtered("payment_account_id")[:1].payment_account_id
        if account:
            return account

        raise ValidationError(
            _(
                "No se pudo determinar la cuenta puente de Cheques propios. "
                "Configurá una cuenta en Pagos salientes > Cheques propios del diario %s."
            )
            % (self.journal_id.display_name or "")
        )

    def _get_bank_account_for_debit(self):
        self.ensure_one()
        if not self.journal_id:
            raise ValidationError(_("El cheque %s no tiene Diario banco configurado.") % self.display_name)
        if not self.journal_id.default_account_id:
            raise ValidationError(
                _("El diario %s no tiene cuenta bancaria/default configurada.") % self.journal_id.display_name
            )
        return self.journal_id.default_account_id

    def _prepare_debit_move_vals(self):
        self.ensure_one()
        if not self.amount:
            raise ValidationError(_("El cheque %s no tiene importe para debitar.") % self.display_name)

        pending_account = self._get_own_check_pending_account()
        bank_account = self._get_bank_account_for_debit()
        partner = self.partner_id
        date = self.env.context.get("dflex_debit_date") or fields.Date.context_today(self)
        ref = _("Débito cheque propio %s") % (self.name or self.display_name)

        return {
            "move_type": "entry",
            "journal_id": self.journal_id.id,
            "date": date,
            "ref": ref,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "account_id": pending_account.id,
                        "partner_id": partner.id or False,
                        "debit": self.amount,
                        "credit": 0.0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "account_id": bank_account.id,
                        "partner_id": partner.id or False,
                        "debit": 0.0,
                        "credit": self.amount,
                    },
                ),
            ],
        }

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

    def action_deliver(self):
        for check in self:
            if check.state != "available":
                raise ValidationError(_("Solo se pueden entregar cheques en estado En Cartera."))
            check.state = "delivered"

    def _get_reverse_counterpart_account(self, pending_account):
        self.ensure_one()

        payment = self.payment_id
        if not payment or not payment.move_id:
            raise ValidationError(
                _("El cheque %s no tiene un pago/asiento relacionado para reversar.") % self.display_name
            )

        move_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id != pending_account)
        partner_lines = move_lines.filtered(
            lambda line: line.account_id.account_type in ("liability_payable", "asset_receivable")
        )
        if self.partner_id:
            partner_lines = partner_lines.filtered(lambda line: line.partner_id == self.partner_id) or partner_lines

        counterpart_line = partner_lines[:1] or move_lines.filtered(lambda line: line.balance)[:1]
        if not counterpart_line:
            raise ValidationError(
                _("No se pudo determinar la cuenta de proveedor/contrapartida para el cheque %s.")
                % self.display_name
            )
        return counterpart_line.account_id

    def _prepare_reverse_payment_move_vals(self, reason):
        self.ensure_one()

        if not self.amount:
            raise ValidationError(_("El cheque %s no tiene importe para reversar.") % self.display_name)
        if not self.payment_id or not self.payment_id.move_id:
            raise ValidationError(_("El cheque %s no tiene pago/asiento relacionado.") % self.display_name)

        pending_account = self._get_own_check_pending_account()
        counterpart_account = self._get_reverse_counterpart_account(pending_account)

        payment_move = self.payment_id.move_id
        pending_lines = payment_move.line_ids.filtered(lambda line: line.account_id == pending_account)
        pending_balance = sum(pending_lines.mapped("balance"))
        if not pending_lines or not pending_balance:
            raise ValidationError(
                _("No se encontró la línea de cuenta puente en el asiento del pago %s.")
                % payment_move.display_name
            )

        partner = self.partner_id or self.payment_id.partner_id
        date = fields.Date.context_today(self)
        ref = _("%s cheque propio %s") % (reason, self.name or self.display_name)

        # Asiento contrario al asiento del pago, solo por el importe de este cheque.
        # Si el pago acreditó la cuenta puente, ahora se debita; si el pago la debitó,
        # ahora se acredita.
        if pending_balance < 0:
            pending_debit = self.amount
            pending_credit = 0.0
            counterpart_debit = 0.0
            counterpart_credit = self.amount
        else:
            pending_debit = 0.0
            pending_credit = self.amount
            counterpart_debit = self.amount
            counterpart_credit = 0.0

        return {
            "move_type": "entry",
            "journal_id": (self.journal_id or self.payment_id.journal_id).id,
            "date": date,
            "ref": ref,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "account_id": pending_account.id,
                        "partner_id": partner.id or False,
                        "debit": pending_debit,
                        "credit": pending_credit,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "account_id": counterpart_account.id,
                        "partner_id": partner.id or False,
                        "debit": counterpart_debit,
                        "credit": counterpart_credit,
                    },
                ),
            ],
        }

    def _create_reverse_payment_move(self, reason):
        for check in self:
            if check.reversal_move_id:
                if check.reversal_move_id.state != "posted":
                    check.reversal_move_id.action_post()
                continue

            reverse_move = self.env["account.move"].create(check._prepare_reverse_payment_move_vals(reason))
            reverse_move.action_post()
            check.reversal_move_id = reverse_move.id

    def action_debit(self):
        for check in self:
            if check.state not in ["delivered", "pending_entry", "expired"]:
                raise ValidationError(_("Solo se pueden debitar cheques Entregados, Por ingresar o Vencidos."))

            if "debit_move_id" in check._fields and check.debit_move_id:
                if check.debit_move_id.state != "posted":
                    check.debit_move_id.action_post()
                check.state = "debited"
                continue

            debit_move = self.env["account.move"].create(check._prepare_debit_move_vals())
            debit_move.action_post()
            check.write({"debit_move_id": debit_move.id, "state": "debited"})

    def action_cancel(self):
        for check in self:
            if check.state == "debited":
                raise ValidationError(_("No se puede anular un cheque ya pagado."))
            if check.state in ["delivered", "pending_entry", "expired"] and check.payment_id:
                check._create_reverse_payment_move(_("Anulación"))
            check.state = "cancelled"

    def action_return(self):
        for check in self:
            if check.state not in ["delivered", "pending_entry", "expired"]:
                raise ValidationError(_("Solo se pueden marcar como Devueltos cheques Entregados, Por ingresar o Vencidos."))
            check._create_reverse_payment_move(_("Devolución"))
            check.state = "returned"

    def _clear_payment_usage_values(self):
        return {
            "state": "available",
            "payment_id": False,
            "move_id": False,
            "debit_move_id": False,
            "reversal_move_id": False,
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
            if check.reversal_move_id:
                raise ValidationError(
                    _("No se puede volver a En Cartera porque el cheque ya tiene un asiento de anulación/devolución.")
                )
            check.write(check._clear_payment_usage_values())

    @api.onchange("number")
    def _onchange_number(self):
        for rec in self:
            if rec.number:
                rec.name = str(rec.number)
