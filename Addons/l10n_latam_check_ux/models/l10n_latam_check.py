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

    # Origen (recibo que generó el cheque)
    origin_move_id = fields.Many2one(
        comodel_name="account.move",
        related="payment_id.move_id",
        string="Asiento Origen",
        readonly=True,
    )

    # Destino (última operación del cheque: depósito / pago proveedor / transferencia / etc.)
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
            last_op = rec._get_last_operation() or rec.payment_id
            rec.last_operation_id = last_op[:1].id if last_op else False

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

    def action_open_origin_payment(self):
        self.ensure_one()
        return self._action_open_form("account.payment", self.payment_id.id)

    def action_open_origin_move(self):
        self.ensure_one()
        move = self.payment_id.move_id
        if move:
            return self._action_open_form("account.move", move.id)
        return self.action_open_origin_payment()

    def action_open_destination_payment(self):
        self.ensure_one()
        if self.last_operation_id:
            return self._action_open_form("account.payment", self.last_operation_id.id)
        return self.action_open_origin_payment()

    def action_open_destination_move(self):
        self.ensure_one()
        move = self.last_operation_move_id
        if move:
            return self._action_open_form("account.move", move.id)
        return self.action_open_destination_payment()

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
