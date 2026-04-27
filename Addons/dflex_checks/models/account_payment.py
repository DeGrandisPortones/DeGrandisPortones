from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dflex_check_line_ids = fields.One2many(
        "dflex.payment.check.line",
        "payment_id",
        string="Cheques propios",
        copy=False,
    )
    dflex_own_check_total = fields.Monetary(
        string="Total cheques propios",
        compute="_compute_dflex_own_check_total",
        currency_field="currency_id",
    )

    # Compatibilidad con versiones anteriores del módulo que usaban un solo cheque en el encabezado.
    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque propio",
        domain="[(\"state\", \"=\", \"available\"), (\"company_id\", \"=\", company_id), (\"journal_id\", \"=\", journal_id)]",
        help="Campo legado. Usar las líneas de cheques propios.",
        copy=False,
    )
    dflex_check_type = fields.Selection(related="dflex_check_id.type", string="Tipo cheque propio", readonly=True)
    dflex_check_payment_date = fields.Date(
        string="Fecha del cheque",
        copy=False,
        help="Campo legado. Usar la fecha en la línea del cheque propio.",
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado cheque propio",
        store=True,
        readonly=True,
    )

    @api.depends("dflex_check_line_ids.amount")
    def _compute_dflex_own_check_total(self):
        for payment in self:
            payment.dflex_own_check_total = sum(payment.dflex_check_line_ids.mapped("amount"))

    def _dflex_is_own_check_payment(self):
        self.ensure_one()
        if self.payment_type != "outbound":
            return False
        payment_method_line = self.payment_method_line_id
        if not payment_method_line:
            return False
        method_code = payment_method_line.code or payment_method_line.payment_method_id.code
        method_name = " ".join(
            part for part in [payment_method_line.name, payment_method_line.payment_method_id.name] if part
        ).lower()
        return bool(
            method_code == "own_checks"
            or "cheques propios" in method_name
            or "own check" in method_name
        )

    def _dflex_has_own_check_lines(self):
        self.ensure_one()
        return bool(self.dflex_check_line_ids or self.dflex_check_id)

    def _compute_l10n_latam_check_warning_msg(self):
        """Suppress the native LATAM check amount warning for DFlex own checks.

        The native LATAM warning compares the payment amount against the hidden
        l10n_latam_new_check_ids table. For DFlex own checks, the real checks
        are loaded in dflex_check_line_ids, so that native warning does not
        apply. We keep the native computation for all other payment flows.
        """
        super_method = getattr(super(), "_compute_l10n_latam_check_warning_msg", None)
        if super_method:
            super_method()
        for payment in self:
            if (
                "l10n_latam_check_warning_msg" in payment._fields
                and payment._dflex_is_own_check_payment()
                and payment._dflex_has_own_check_lines()
            ):
                payment.l10n_latam_check_warning_msg = False

    @api.onchange("payment_method_line_id", "payment_type")
    def _onchange_dflex_check_payment_method(self):
        for payment in self:
            if not payment._dflex_is_own_check_payment():
                payment.dflex_check_id = False
                payment.dflex_check_payment_date = False
                payment.dflex_check_line_ids = [(5, 0, 0)]

    @api.onchange("journal_id")
    def _onchange_dflex_check_journal_id(self):
        for payment in self:
            if not payment.dflex_check_line_ids:
                continue
            invalid_lines = payment.dflex_check_line_ids.filtered(
                lambda line: line.check_id and line.check_id.journal_id and line.check_id.journal_id != payment.journal_id
            )
            if invalid_lines:
                payment.dflex_check_line_ids = [(2, line.id, 0) for line in invalid_lines if line.id]
                return {
                    "warning": {
                        "title": _("Cheques propios quitados"),
                        "message": _("Se quitaron cheques propios que no pertenecen al diario seleccionado."),
                    }
                }

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id(self):
        """Legacy compatibility: convert old single field into one line."""
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue
            if not payment.dflex_check_line_ids.filtered(lambda line: line.check_id == check):
                payment.dflex_check_line_ids = [
                    (0, 0, {
                        "check_id": check.id,
                        "check_payment_date": payment.dflex_check_payment_date or check.payment_date or payment.date,
                        "amount": payment.amount or check.amount or 0.0,
                    })
                ]

    @api.onchange("dflex_check_line_ids")
    def _onchange_dflex_check_line_ids(self):
        for payment in self:
            total = sum(payment.dflex_check_line_ids.mapped("amount"))
            if total and payment._dflex_is_own_check_payment():
                payment.amount = total
            if (
                "l10n_latam_check_warning_msg" in payment._fields
                and payment._dflex_is_own_check_payment()
                and payment._dflex_has_own_check_lines()
            ):
                payment.l10n_latam_check_warning_msg = False

    @api.constrains("dflex_check_line_ids", "company_id", "payment_type", "payment_method_line_id", "journal_id")
    def _constrains_dflex_check_lines(self):
        for payment in self:
            if not payment.dflex_check_line_ids:
                continue
            if not payment._dflex_is_own_check_payment():
                raise ValidationError(
                    _("Los cheques propios de chequera solo pueden usarse en pagos salientes con método Own Checks.")
                )

    def _dflex_validate_checks_before_post(self):
        for payment in self:
            if payment._dflex_is_own_check_payment() and not payment.dflex_check_line_ids:
                raise ValidationError(_("Debe cargar al menos un cheque propio para confirmar un pago con Own Checks."))

            if not payment.dflex_check_line_ids:
                continue

            if not payment._dflex_is_own_check_payment():
                raise ValidationError(_("Los cheques propios solo pueden usarse con el método de pago Own Checks."))

            checks = payment.dflex_check_line_ids.mapped("check_id")
            if len(checks) != len(payment.dflex_check_line_ids):
                raise ValidationError(_("Hay líneas de cheques propios sin número de cheque."))
            if len(checks) != len(set(checks.ids)):
                raise ValidationError(_("No se puede repetir el mismo cheque propio en un pago."))

            precision = payment.currency_id.rounding
            if float_compare(payment.amount, payment.dflex_own_check_total, precision_rounding=precision) != 0:
                raise ValidationError(
                    _("El importe del pago (%s) debe coincidir con el total de cheques propios (%s).")
                    % (payment.amount, payment.dflex_own_check_total)
                )

            for line in payment.dflex_check_line_ids:
                check = line.check_id
                if check.company_id != payment.company_id:
                    raise ValidationError(_("El cheque %s pertenece a otra compañía.") % check.display_name)
                if check.journal_id and check.journal_id != payment.journal_id:
                    raise ValidationError(
                        _("El cheque %s pertenece al diario %s y no al diario %s.")
                        % (check.display_name, check.journal_id.display_name, payment.journal_id.display_name)
                    )
                if check.payment_id and check.payment_id != payment:
                    raise ValidationError(
                        _("El cheque %s ya está vinculado al pago %s.")
                        % (check.display_name, check.payment_id.display_name)
                    )
                if check.state != "available" and check.payment_id != payment:
                    selection = dict(check._fields["state"].selection)
                    raise ValidationError(
                        _("El cheque %s no está en cartera (estado actual: %s).")
                        % (check.display_name, selection.get(check.state, check.state))
                    )

    def _dflex_write_delivered_checks(self):
        for payment in self.filtered("dflex_check_line_ids"):
            for line in payment.dflex_check_line_ids:
                check = line.check_id
                check.write(
                    {
                        "state": "delivered",
                        "payment_id": payment.id,
                        "payment_line_id": line.id,
                        "move_id": payment.move_id.id or False,
                        "issue_date": payment.date,
                        "payment_date": line.check_payment_date or payment.date,
                        "delivery_date": fields.Date.context_today(payment),
                        "amount": line.amount,
                        "currency_id": payment.currency_id.id,
                        "partner_id": payment.partner_id.id or False,
                    }
                )

    def _dflex_release_checks(self):
        for payment in self.filtered("dflex_check_line_ids"):
            for line in payment.dflex_check_line_ids:
                check = line.check_id
                if check.payment_id != payment:
                    continue
                if check.state == "debited":
                    raise ValidationError(
                        _("No se puede liberar el cheque %s porque ya está ingresado.") % check.display_name
                    )
                check.write(check._clear_payment_usage_values())

    def _dflex_sync_check_states_from_payments(self):
        checks = self.mapped("dflex_check_line_ids.check_id") | self.mapped("dflex_check_id")
        checks._update_operational_state()

    def action_post(self):
        self._dflex_validate_checks_before_post()
        # La validación nativa de LATAM compara el monto contra l10n_latam_new_check_ids.
        # En este flujo esa tabla está oculta y se usa dflex_check_line_ids, por eso pasamos
        # contexto para que l10n_latam_check_ux no bloquee con un falso positivo.
        post_self = self
        if any(payment._dflex_has_own_check_lines() for payment in self):
            post_self = self.with_context(dflex_skip_l10n_latam_check_warning=True)
        res = super(AccountPayment, post_self).action_post()
        self._dflex_write_delivered_checks()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._dflex_sync_check_states_from_payments()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._dflex_release_checks()
        return res

    def action_draft(self):
        res = super().action_draft()
        self._dflex_release_checks()
        return res

    def action_dflex_mark_check_returned(self):
        """Marcar los cheques del pago como devueltos/rechazados."""
        for payment in self:
            checks = payment.dflex_check_line_ids.mapped("check_id") | payment.dflex_check_id
            for check in checks:
                if check.payment_id and check.payment_id != payment:
                    raise ValidationError(
                        _("El cheque %s está vinculado a otro pago (%s).")
                        % (check.display_name, check.payment_id.display_name)
                    )
                if check.state not in ["delivered", "pending_entry"]:
                    selection = dict(check._fields["state"].selection)
                    raise ValidationError(
                        _("Solo se puede marcar como Devuelto un cheque Entregado o Por ingresar. Estado actual: %s")
                        % selection.get(check.state, check.state)
                    )
                check.write({"state": "returned", "payment_id": payment.id})
        return True
