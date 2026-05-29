from odoo import _, fields, models
from odoo.exceptions import UserError


class DgResumenCtaCteSummary(models.TransientModel):
    _name = "dg.resumen.cta.cte.summary"
    _description = "Resumen Cta Cte - Listado"
    _order = "partner_id"

    wizard_id = fields.Many2one(
        "dg.account.statement.wizard",
        string="Filtro",
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one("res.company", string="Empresa", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
    date_from = fields.Date(string="Desde", readonly=True)
    date_to = fields.Date(string="Hasta", readonly=True)
    include_initial_balance = fields.Boolean(string="Incluye saldo anterior", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda", readonly=True)
    subtotal_fca = fields.Monetary(
        string="Subtotal FCA",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )
    subtotal_internas = fields.Monetary(
        string="Subtotal Internas",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )
    total_balance = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )

    def action_open_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.partner_id.display_name,
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_download_resumen(self):
        if not self:
            raise UserError(_("Seleccione al menos un cliente para descargar el resumen."))

        companies = self.mapped("company_id")
        if len(companies) != 1:
            raise UserError(_("Seleccione clientes de una sola empresa para imprimir el resumen."))

        first = self[0]
        for line in self:
            if (
                line.date_from != first.date_from
                or line.date_to != first.date_to
                or line.include_initial_balance != first.include_initial_balance
            ):
                raise UserError(_("Seleccione lineas con el mismo rango de fechas."))

        partners = self.mapped("partner_id")
        wizard = self.env["dg.account.statement.wizard"].create(
            {
                "company_id": companies.id,
                "date_from": first.date_from,
                "date_to": first.date_to,
                "include_initial_balance": first.include_initial_balance,
                "partner_ids": [(6, 0, partners.ids)],
            }
        )
        return wizard.action_print_pdf()
