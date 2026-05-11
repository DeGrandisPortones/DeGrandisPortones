from odoo import api, fields, models


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    ux_is_company_issuer = fields.Boolean(
        string="Cheque propio / emisor empresa",
        compute="_compute_ux_is_company_issuer",
        search="_search_ux_is_company_issuer",
        index=True,
        help=(
            "Campo tecnico para excluir cheques propios de la accion Cheques de Terceros. "
            "Se marca cuando el cheque esta vinculado a un cheque propio DFlex, cuando el metodo "
            "del pago es Cheques propios, o cuando el emisor coincide con la empresa."
        ),
    )

    def _ux_normalize_vat(self, vat):
        return "".join(ch for ch in (vat or "") if ch.isdigit())

    def _ux_normalize_text(self, text):
        return " ".join((text or "").strip().lower().split())

    def _ux_get_field_value_safe(self, field_name):
        self.ensure_one()
        return self[field_name] if field_name in self._fields else False

    def _ux_get_nested_field_value_safe(self, record, field_path):
        current = record
        for field_name in field_path.split("."):
            if not current or field_name not in current._fields:
                return False
            current = current[field_name]
        return current

    def _ux_get_company_issuer_names(self):
        self.ensure_one()
        partner = self.company_id.partner_id
        names = {
            self._ux_normalize_text(self.company_id.name),
            self._ux_normalize_text(partner.name),
            self._ux_normalize_text(partner.commercial_company_name),
            self._ux_normalize_text(partner.display_name),
        }
        names.discard("")
        return names

    def _ux_is_own_company_check_line(self):
        self.ensure_one()

        if "dflex_check_id" in self._fields and self.dflex_check_id:
            return True

        payment = self.payment_id
        method_line = payment.payment_method_line_id if payment else self.env["account.payment.method.line"]
        method = method_line.payment_method_id if method_line else self.env["account.payment.method"]
        method_parts = [
            self._ux_get_field_value_safe("payment_method_code"),
            method_line.code if method_line else False,
            method_line.name if method_line else False,
            method.code if method else False,
            method.name if method else False,
        ]
        method_haystack = self._ux_normalize_text(" ".join(str(part) for part in method_parts if part))
        if (
            "own_checks" in method_haystack
            or "own checks" in method_haystack
            or "cheques propios" in method_haystack
            or "cheque propio" in method_haystack
        ):
            return True

        company_partner = self.company_id.partner_id
        company_vat = self._ux_normalize_vat(company_partner.vat)

        issuer_vats = {
            self._ux_normalize_vat(self._ux_get_field_value_safe("issuer_vat")),
            self._ux_normalize_vat(self._ux_get_field_value_safe("owner_vat")),
            self._ux_normalize_vat(self._ux_get_field_value_safe("ux_history_issuer_vat")),
        }
        issuer_vats.discard("")
        if company_vat and company_vat in issuer_vats:
            return True

        company_names = self._ux_get_company_issuer_names()
        issuer_names = {
            self._ux_normalize_text(self._ux_get_field_value_safe("issuer_name")),
            self._ux_normalize_text(self._ux_get_field_value_safe("owner_name")),
            self._ux_normalize_text(self._ux_get_field_value_safe("x_studio_emisor_nombre")),
            self._ux_normalize_text(self._ux_get_field_value_safe("ux_history_issuer_name")),
        }
        issuer_names.discard("")

        for issuer_name in issuer_names:
            if issuer_name in company_names:
                return True
            if issuer_name and any(company_name.startswith(issuer_name) for company_name in company_names):
                return True
            if issuer_name and any(issuer_name.startswith(company_name) for company_name in company_names):
                return True

        return False

    @api.depends(
        "issuer_vat",
        "payment_method_code",
        "payment_id",
        "payment_id.payment_method_line_id",
        "payment_id.payment_method_line_id.code",
        "payment_id.payment_method_line_id.name",
        "payment_id.payment_method_line_id.payment_method_id",
        "payment_id.payment_method_line_id.payment_method_id.code",
        "payment_id.payment_method_line_id.payment_method_id.name",
        "company_id",
        "company_id.name",
        "company_id.partner_id",
        "company_id.partner_id.vat",
        "company_id.partner_id.name",
        "company_id.partner_id.commercial_company_name",
    )
    def _compute_ux_is_company_issuer(self):
        for check in self:
            check.ux_is_company_issuer = check._ux_is_own_company_check_line()

    def _search_ux_is_company_issuer(self, operator, value):
        checks = self.sudo().with_context(active_test=False).search([])
        own_ids = checks.filtered(lambda check: check._ux_is_own_company_check_line()).ids

        positive = (operator in ("=", "==") and bool(value)) or (operator in ("!=", "<>") and not bool(value))
        if positive:
            return [("id", "in", own_ids or [0])]
        if not own_ids:
            return []
        return [("id", "not in", own_ids)]

    def _dflex_own_check_destination_label(self):
        self.ensure_one()
        dflex_state = False
        if "dflex_check_id" in self._fields and self.dflex_check_id:
            dflex_state = self.dflex_check_id.state

        if dflex_state == "available":
            return "En cartera"
        if dflex_state == "debited":
            return "Depositado"
        if self.payment_id and self.payment_id.state not in ("draft", "canceled"):
            return "Entregado"
        if dflex_state in ("delivered", "pending_entry", "expired", "returned", "cancelled"):
            return "Entregado"
        return False

    def _compute_ux_check_state(self):
        res = super()._compute_ux_check_state()
        for check in self:
            label = check._dflex_own_check_destination_label() if check._ux_is_own_company_check_line() else False
            if label == "En cartera":
                check.ux_check_state = "in_wallet"
            elif label == "Depositado":
                check.ux_check_state = "deposited"
            elif label == "Entregado":
                check.ux_check_state = "delivered"
        return res

    def _compute_ux_history_summary_fields(self):
        res = super()._compute_ux_history_summary_fields()
        for check in self:
            if not check._ux_is_own_company_check_line():
                continue

            label = check._dflex_own_check_destination_label()
            if not label:
                continue

            check.ux_destination_type = label

            if label == "En cartera":
                destination = check.payment_id.journal_id.display_name if check.payment_id else False
                check.ux_destination = "Ingreso: %s" % destination if destination else False
            else:
                partner = check.payment_id.partner_id if check.payment_id else self.env["res.partner"]
                check.ux_destination = partner.display_name or label

            operation_date = False
            if check.payment_id:
                operation_date = check.payment_id.l10n_latam_move_check_ids_operation_date
                if not operation_date and check.payment_id.date:
                    operation_date = fields.Datetime.to_datetime(check.payment_id.date)
            check.ux_destination_movement_date = operation_date
        return res

    @api.model
    def _dflex_third_party_all_domain(self):
        return (
            "[('payment_method_code', '=', 'new_third_party_checks'), "
            "('payment_state', '!=', 'draft'), "
            "('ux_is_company_issuer', '=', False)]"
        )

    @api.model
    def _dflex_third_party_in_wallet_domain(self):
        # Backward-compatible method name. The main Cheques de terceros menu
        # must show all third-party checks; use the search filters to narrow
        # to En cartera / Entregado / Depositado / Vendido.
        return self._dflex_third_party_all_domain()

    @api.model
    def _dflex_update_third_party_check_actions(self):
        domain = self._dflex_third_party_all_domain()
        actions = self.env["ir.actions.act_window"].sudo().search([("res_model", "=", "l10n_latam.check")])
        actions = actions.filtered(
            lambda action: (
                "new_third_party_checks" in (action.domain or "")
                or "tercer" in (action.name or "").lower()
                or "third" in (action.name or "").lower()
            )
        )
        actions.write({"domain": domain})
        return True

    @api.model
    def _dflex_recompute_third_party_filter_fields(self):
        self._dflex_update_third_party_check_actions()
        checks = self.search([])
        if checks:
            checks._compute_ux_is_company_issuer()
            checks._compute_ux_check_state()
            if hasattr(checks, "_compute_ux_history_summary_fields"):
                checks._compute_ux_history_summary_fields()
        return True
