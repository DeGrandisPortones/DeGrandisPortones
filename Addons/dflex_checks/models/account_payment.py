from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Campos legacy: se conservan para no romper vistas/datos viejos, pero el flujo nuevo
    # usa l10n_latam_new_check_ids.dflex_check_id en la solapa nativa Cheques.
    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque propio",
        domain="[(\"state\", \"=\", \"available\"), (\"company_id\", \"=\", company_id), (\"journal_id\", \"=\", journal_id)]",
        help="Campo legado. Usar la solapa Cheques.",
        copy=False,
    )
    dflex_check_type = fields.Selection(related="dflex_check_id.type", string="Tipo cheque propio", readonly=True)
    dflex_check_payment_date = fields.Date(
        string="Fecha del cheque",
        copy=False,
        help="Campo legado. Usar la fecha en la línea de la solapa Cheques.",
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado cheque propio",
        store=True,
        readonly=True,
    )

    dflex_own_check_total = fields.Monetary(
        string="Total cheques propios",
        compute="_compute_dflex_own_check_total",
        currency_field="currency_id",
    )

    @api.depends("l10n_latam_new_check_ids.amount", "l10n_latam_new_check_ids.dflex_check_id")
    def _compute_dflex_own_check_total(self):
        for payment in self:
            payment.dflex_own_check_total = sum(payment._dflex_get_native_own_check_lines().mapped("amount"))

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

    def _dflex_get_native_own_check_lines(self):
        self.ensure_one()
        if "l10n_latam_new_check_ids" not in self._fields:
            return self.env["l10n_latam.check"]
        return self.l10n_latam_new_check_ids.filtered("dflex_check_id")

    @api.onchange("payment_method_line_id", "payment_type")
    def _onchange_dflex_check_payment_method(self):
        for payment in self:
            if not payment._dflex_is_own_check_payment():
                payment.dflex_check_id = False
                payment.dflex_check_payment_date = False

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id(self):
        """Compatibilidad legacy: si alguien usa el campo viejo, crea una línea nativa."""
        for payment in self:
            check = payment.dflex_check_id
            if not check:
                continue
            if "l10n_latam_new_check_ids" not in payment._fields:
                continue
            if not payment.l10n_latam_new_check_ids.filtered(lambda line: line.dflex_check_id == check):
                payment.l10n_latam_new_check_ids = [
                    (0, 0, {
                        "dflex_check_id": check.id,
                        "name": check.name,
                        "bank_id": check.bank_id.id if check.bank_id else False,
                        "payment_date": payment.dflex_check_payment_date or check.payment_date or payment.date,
                        "amount": payment.amount or check.amount or 0.0,
                    })
                ]

    def _dflex_validate_native_own_checks_before_post(self):
        for payment in self:
            native_lines = payment._dflex_get_native_own_check_lines()

            if not native_lines:
                # No bloqueamos el flujo estándar si no usan cheques generados por DFlex.
                continue

            if not payment._dflex_is_own_check_payment():
                raise ValidationError(_("Los cheques propios DFlex solo pueden usarse con el método Cheques propios."))

            checks = native_lines.mapped("dflex_check_id")
            if len(checks) != len(native_lines):
                raise ValidationError(_("Hay líneas sin número de cheque propio."))
            if len(checks) != len(set(checks.ids)):
                raise ValidationError(_("No se puede repetir el mismo cheque propio en un pago."))

            total_checks = sum(native_lines.mapped("amount"))
            precision = payment.currency_id.rounding
            if float_compare(payment.amount, total_checks, precision_rounding=precision) != 0:
                raise ValidationError(
                    _("El importe del pago (%s) debe coincidir con el total de cheques propios (%s).")
                    % (payment.amount, total_checks)
                )

            for line in native_lines:
                check = line.dflex_check_id
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

    def _dflex_write_delivered_native_checks(self):
        for payment in self:
            for line in payment._dflex_get_native_own_check_lines():
                check = line.dflex_check_id
                check.write(
                    {
                        "state": "delivered",
                        "payment_id": payment.id,
                        "payment_line_id": False,
                        "move_id": payment.move_id.id or False,
                        "issue_date": payment.date,
                        "payment_date": line.payment_date or payment.date,
                        "delivery_date": fields.Date.context_today(payment),
                        "amount": line.amount,
                        "currency_id": payment.currency_id.id,
                        "partner_id": payment.partner_id.id or False,
                    }
                )

    def _dflex_release_native_checks(self):
        for payment in self:
            for line in payment._dflex_get_native_own_check_lines():
                check = line.dflex_check_id
                if check.payment_id != payment:
                    continue
                if check.state == "debited":
                    raise ValidationError(
                        _("No se puede liberar el cheque %s porque ya está ingresado.") % check.display_name
                    )
                check.write(check._clear_payment_usage_values())

    def _dflex_sync_check_states_from_payments(self):
        checks = self.mapped("l10n_latam_new_check_ids.dflex_check_id") | self.mapped("dflex_check_id")
        checks._update_operational_state()

    def action_post(self):
        self._dflex_validate_native_own_checks_before_post()
        res = super().action_post()
        self._dflex_write_delivered_native_checks()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._dflex_sync_check_states_from_payments()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self._dflex_release_native_checks()
        return res

    def action_draft(self):
        res = super().action_draft()
        self._dflex_release_native_checks()
        return res

    def action_dflex_mark_check_returned(self):
        for payment in self:
            checks = payment._dflex_get_native_own_check_lines().mapped("dflex_check_id") | payment.dflex_check_id
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
