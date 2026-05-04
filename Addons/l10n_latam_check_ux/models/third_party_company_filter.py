from odoo import api, fields, models


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    ux_is_company_issuer = fields.Boolean(
        string="Emisor es la empresa",
        compute="_compute_ux_is_company_issuer",
        store=True,
        index=True,
        help="Campo técnico para excluir cheques propios de la acción Cheques de Terceros.",
    )

    def _ux_normalize_vat(self, vat):
        return "".join(ch for ch in (vat or "") if ch.isdigit())

    @api.depends("issuer_vat", "company_id", "company_id.partner_id", "company_id.partner_id.vat")
    def _compute_ux_is_company_issuer(self):
        for check in self:
            issuer_vat = check._ux_normalize_vat(check.issuer_vat)
            company_vat = check._ux_normalize_vat(check.company_id.partner_id.vat)
            check.ux_is_company_issuer = bool(issuer_vat and company_vat and issuer_vat == company_vat)

    def _register_hook(self):
        res = super()._register_hook()
        action = self.env.ref("l10n_latam_check.action_third_party_check", raise_if_not_found=False)
        if action:
            action.domain = (
                "[('payment_method_code', '=', 'new_third_party_checks'), "
                "('payment_state', '!=', 'draft'), "
                "('ux_is_company_issuer', '=', False)]"
            )
        return res
