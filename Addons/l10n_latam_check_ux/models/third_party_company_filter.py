from odoo import api, fields, models


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    ux_is_company_issuer = fields.Boolean(
        string="Cheque propio / emisor empresa",
        compute="_compute_ux_is_company_issuer",
        store=True,
        index=True,
        help=(
            "Campo técnico para excluir cheques propios de la acción Cheques de Terceros. "
            "Se marca cuando el cheque está vinculado a un cheque propio DFlex, cuando el método "
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
        issuer_vat = self._ux_normalize_vat(
            self._ux_get_field_value_safe("issuer_vat")
            or self._ux_get_field_value_safe("owner_vat")
        )
        if issuer_vat and company_vat and issuer_vat == company_vat:
            return True

        company_names = {
            self._ux_normalize_text(self.company_id.name),
            self._ux_normalize_text(company_partner.name),
            self._ux_normalize_text(company_partner.commercial_company_name),
            self._ux_normalize_text(company_partner.display_name),
        }
        company_names.discard("")

        issuer_names = {
            self._ux_normalize_text(self._ux_get_field_value_safe("issuer_name")),
            self._ux_normalize_text(self._ux_get_field_value_safe("owner_name")),
            self._ux_normalize_text(self._ux_get_field_value_safe("x_studio_emisor_nombre")),
        }
        issuer_names.discard("")

        # Casos vistos en producción: el emisor puede venir como "VERT" o como razón social completa.
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
        "owner_vat",
        "issuer_name",
        "owner_name",
        "x_studio_emisor_nombre",
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

    def _compute_ux_check_state(self):
        res = super()._compute_ux_check_state()
        for check in self:
            if not check._ux_is_own_company_check_line():
                continue

            dflex_state = False
            if "dflex_check_id" in check._fields and check.dflex_check_id:
                dflex_state = check.dflex_check_id.state

            if dflex_state == "available":
                check.ux_check_state = "in_wallet"
            elif dflex_state in ("delivered", "pending_entry", "expired", "returned", "cancelled"):
                check.ux_check_state = "delivered"
            elif dflex_state == "debited":
                check.ux_check_state = "deposited"
            elif check.payment_id and check.payment_id.state not in ("draft", "canceled"):
                # Un cheque propio emitido en una orden de pago ya no está en cartera.
                check.ux_check_state = "delivered"
        return res

    @api.model
    def _dflex_recompute_third_party_filter_fields(self):
        checks = self.search([])
        if checks:
            checks._compute_ux_is_company_issuer()
            checks._compute_ux_check_state()
            if hasattr(checks, "_compute_ux_history_summary_fields"):
                checks._compute_ux_history_summary_fields()
        return True
