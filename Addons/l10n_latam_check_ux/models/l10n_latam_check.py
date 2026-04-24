from odoo import _, api, fields, models


class l10nLatamAccountPaymentCheck(models.Model):
    _inherit = "l10n_latam.check"

    check_add_debit_button = fields.Boolean(related="original_journal_id.check_add_debit_button", readonly=True)

    first_operation = fields.Many2one(
        "account.payment",
        compute="_compute_first_operation",
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Origen (recibo/pago que creó el cheque)
    # -------------------------------------------------------------------------
    # Compat: algunos XML usan `payment_move_id`, otros `origin_move_id`
    payment_move_id = fields.Many2one(
        comodel_name="account.move",
        related="payment_id.move_id",
        string="Asiento Origen",
        readonly=True,
    )
    origin_move_id = fields.Many2one(
        comodel_name="account.move",
        related="payment_id.move_id",
        string="Asiento Origen",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Destino (última operación del cheque: depósito / pago proveedor / transf. / etc.)
    # -------------------------------------------------------------------------
    last_operation_id = fields.Many2one(
        "account.payment",
        compute="_compute_last_operation_id",
        store=True,
        readonly=True,
        string="Operación Destino",
    )
    last_operation_move_id = fields.Many2one(
        comodel_name="account.move",
        related="last_operation_id.move_id",
        string="Asiento Destino",
        readonly=True,
    )
    last_operation_partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="last_operation_id.partner_id",
        string="Partner Destino",
        readonly=True,
    )
    last_operation_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="last_operation_id.journal_id",
        string="Diario Destino",
        readonly=True,
    )

    date = fields.Date(related="first_operation.date")
    memo = fields.Char(related="payment_id.memo")

    company_id = fields.Many2one(
        compute="_compute_company_id", store=True, compute_sudo=True, comodel_name="res.company"
    )
    operation_ids = fields.Many2many(check_company=False)
    payment_state = fields.Selection(
        related="payment_id.state",
        readonly=True,
    )

    @api.depends(
        "operation_ids.state",
        "operation_ids.l10n_latam_move_check_ids_operation_date",
        "payment_id.state",
        "payment_id.l10n_latam_move_check_ids_operation_date",
    )
    def _compute_last_operation_id(self):
        for rec in self:
            ops = (rec.payment_id + rec.operation_ids).filtered(lambda p: p.state not in ["draft", "canceled"])
            ops_with_date = ops.filtered(lambda p: p.l10n_latam_move_check_ids_operation_date)
            if ops_with_date:
                last = ops_with_date.sorted(key=lambda p: (p.l10n_latam_move_check_ids_operation_date, p.id))[-1:]
            else:
                last = ops.sorted(key=lambda p: (p.date, p.id))[-1:] if ops else self.env["account.payment"]
            rec.last_operation_id = last[:1].id if last else False

    @api.depends("operation_ids.state", "payment_id.state")
    def _compute_company_id(self):
        for rec in self:
            last_operation = rec._get_last_operation() or rec.payment_id
            rec.company_id = last_operation.company_id

    @api.depends("operation_ids.state", "payment_id.state")
    def _compute_first_operation(self):
        for rec in self:
            all_operations = rec.payment_id + rec.operation_ids
            valid_ops = all_operations.filtered(lambda x: x.state in ["in_process", "paid"])
            sorted_ops = valid_ops.sorted(key=lambda payment: (payment.date, payment._origin.id))
            rec.first_operation = sorted_ops[:1].id or False

    def button_open_check_operations(self):
        action = super(l10nLatamAccountPaymentCheck, self.sudo()).button_open_check_operations()
        self.ensure_one()
        operations = self.operation_ids.sorted(lambda r: r.l10n_latam_move_check_ids_operation_date, reverse=True)
        operations = (operations + self.payment_id).filtered(
            lambda x: x.state not in ["draft", "canceled"] and x.company_id == self.company_id
        )
        action = {
            "name": _("Check Operations"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "views": [
                (self.env.ref("l10n_latam_check.view_account_third_party_check_operations_tree").id, "list"),
                (False, "form"),
            ],
            "context": {"create": False},
            "domain": [("id", "in", operations.ids)],
        }
        return action

    def _get_last_operation(self):
        super()._get_last_operation()
        self.ensure_one()
        return (
            (self.payment_id + self.operation_ids)
            .filtered(lambda x: x.state not in ["draft", "canceled"] and x.l10n_latam_move_check_ids_operation_date)
            .sorted(key=lambda payment: (payment.l10n_latam_move_check_ids_operation_date))[-1:]
        )

    # -------------------------------------------------------------------------
    # Acciones para navegar desde el listado (type="object")
    # -------------------------------------------------------------------------
    def _action_open_form(self, res_model, res_id):
        return {
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "res_id": res_id,
            "views": [(False, "form")],
            "target": "current",
        }

    def action_open_check_form(self):
        self.ensure_one()
        return self._action_open_form("l10n_latam.check", self.id)

    # Compat (v2)
    def action_open_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        return self._action_open_form("account.payment", self.payment_id.id)

    def action_open_payment_move(self):
        self.ensure_one()
        move = self.payment_id.move_id
        if not move:
            return self.action_open_payment()
        return self._action_open_form("account.move", move.id)

    # Nombres nuevos (v3)
    def action_open_origin_payment(self):
        return self.action_open_payment()

    def action_open_origin_move(self):
        return self.action_open_payment_move()

    def action_open_destination_payment(self):
        self.ensure_one()
        if self.last_operation_id:
            return self._action_open_form("account.payment", self.last_operation_id.id)
        return self.action_open_payment()

    def action_open_destination_move(self):
        self.ensure_one()
        move = self.last_operation_move_id
        if move:
            return self._action_open_form("account.move", move.id)
        return self.action_open_destination_payment()

    # -------------------------------------------------------------------------
    # Historial de cheques de terceros
    # -------------------------------------------------------------------------
    def _history_get_first_existing_value(self, field_names):
        self.ensure_one()
        for field_name in field_names:
            if field_name in self._fields and self[field_name]:
                return self[field_name]
        return False

    def _history_get_issue_date(self):
        self.ensure_one()
        return self._history_get_first_existing_value(("issue_date", "emission_date", "date")) or self.payment_id.date

    def _history_get_issuer_vat(self):
        self.ensure_one()
        return self._history_get_first_existing_value(("issuer_vat", "owner_vat")) or ""

    def _history_get_issuer_name(self):
        self.ensure_one()
        issuer_name = self._history_get_first_existing_value(
            ("x_studio_emisor_nombre", "issuer_name", "owner_name")
        )
        if issuer_name:
            return issuer_name
        issuer_vat = self._history_get_issuer_vat()
        if issuer_vat:
            partner = self.env["res.partner"].sudo().search([("vat", "=", issuer_vat)], limit=1)
            if partner:
                return partner.display_name
        return ""

    def _history_get_operations(self):
        self.ensure_one()
        operations = (self.payment_id + self.operation_ids).filtered(lambda p: p.state not in ["draft", "canceled"])

        def _sort_key(payment):
            operation_date = payment.l10n_latam_move_check_ids_operation_date
            if not operation_date and payment.date:
                operation_date = fields.Datetime.to_datetime(payment.date)
            return (operation_date or fields.Datetime.to_datetime("1970-01-01"), payment.id)

        return operations.sorted(key=_sort_key)

    def _history_get_payment_destination(self, payment):
        self.ensure_one()
        if payment == self.payment_id:
            return _("Ingreso: %s") % (payment.journal_id.display_name or payment.display_name)

        if payment.destination_journal_id:
            return payment.destination_journal_id.display_name
        if payment.partner_id:
            return payment.partner_id.display_name
        if payment.journal_id:
            return payment.journal_id.display_name
        return payment.display_name

    def _history_prepare_line_vals(self, payment):
        self.ensure_one()
        origin_partner = self.payment_id.partner_id
        operation_date = payment.l10n_latam_move_check_ids_operation_date
        if not operation_date and payment.date:
            operation_date = fields.Datetime.to_datetime(payment.date)

        return {
            "check_id": self.id,
            "payment_id": payment.id,
            "issue_date": self._history_get_issue_date(),
            "issuer_vat": self._history_get_issuer_vat(),
            "issuer_name": self._history_get_issuer_name(),
            "payment_date": self.payment_date,
            "payment_contact_name": origin_partner.display_name or "",
            "payment_contact_vat": origin_partner.vat or "",
            "destination": self._history_get_payment_destination(payment),
            "destination_movement_date": operation_date,
        }

    def action_open_check_history(self):
        self.ensure_one()
        wizard = self.env["l10n_latam.check.history.wizard"].create(
            {
                "check_id": self.id,
                "line_ids": [(0, 0, self._history_prepare_line_vals(payment)) for payment in self._history_get_operations()],
            }
        )
        return {
            "name": _("Historial del cheque"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_latam.check.history.wizard",
            "res_id": wizard.id,
            "views": [(self.env.ref("l10n_latam_check_ux.l10n_latam_check_history_wizard_view_form").id, "form")],
            "target": "current",
            "context": {"create": False, "edit": False, "delete": False},
        }

    @api.depends("payment_method_line_id.code", "payment_id.partner_id")
    def _compute_bank_id(self):
        payment_method_change = self._origin.payment_method_line_id != self.payment_method_line_id
        partner_id_change = self._origin.payment_id.partner_id != self.payment_id.partner_id
        if payment_method_change or partner_id_change:
            super()._compute_bank_id()

    @api.depends("payment_method_line_id.code", "payment_id.partner_id")
    def _compute_issuer_vat(self):
        payment_method_change = self._origin.payment_method_line_id != self.payment_method_line_id
        partner_id_change = self._origin.payment_id.partner_id != self.payment_id.partner_id
        if payment_method_change or partner_id_change:
            super()._compute_issuer_vat()
