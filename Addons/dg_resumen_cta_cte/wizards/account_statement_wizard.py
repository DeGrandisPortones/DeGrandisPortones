from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class DgAccountStatementWizard(models.TransientModel):
    _name = "dg.account.statement.wizard"
    _description = "Resumen Cta Cte"

    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta", default=fields.Date.context_today, required=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        help="Dejar vacio para listar clientes con movimientos en el rango seleccionado.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
    )
    include_initial_balance = fields.Boolean(
        string="Incluir saldo anterior",
        default=True,
        help="Si se indica una fecha desde, agrega el saldo anterior de cada cuenta antes del rango.",
    )

    def _check_dates(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(_("La fecha desde no puede ser posterior a la fecha hasta."))

    def action_print_pdf(self):
        self.ensure_one()
        self._check_dates()
        if not self.company_id:
            raise UserError(_("Debe seleccionar una empresa."))
        return self.env.ref("dg_resumen_cta_cte.action_report_dg_account_statement").report_action(self)

    def action_view_summary(self):
        self.ensure_one()
        self._check_dates()
        if not self.company_id:
            raise UserError(_("Debe seleccionar una empresa."))

        old_lines = self.env["dg.resumen.cta.cte.summary"].search([("wizard_id", "=", self.id)])
        old_lines.unlink()

        report = self.env["report.dg_resumen_cta_cte.report_account_statement"]
        statements = report._get_wizard_statements(self)
        vals_list = []
        for statement in statements:
            group_amounts = {group["key"]: group["balance"] for group in statement["groups"]}
            subtotal_fca = group_amounts.get("fca", 0.0)
            subtotal_internas = group_amounts.get("internas", 0.0)
            total_balance = statement["total_balance"]
            if abs(total_balance) <= 0.004 and abs(subtotal_fca) <= 0.004 and abs(subtotal_internas) <= 0.004:
                continue
            vals_list.append(
                {
                    "wizard_id": self.id,
                    "company_id": self.company_id.id,
                    "partner_id": statement["partner"].id,
                    "date_from": self.date_from,
                    "date_to": self.date_to,
                    "include_initial_balance": self.include_initial_balance,
                    "currency_id": statement["currency"].id,
                    "subtotal_fca": subtotal_fca,
                    "subtotal_internas": subtotal_internas,
                    "total_balance": total_balance,
                }
            )
        if vals_list:
            self.env["dg.resumen.cta.cte.summary"].create(vals_list)

        return {
            "type": "ir.actions.act_window",
            "name": _("Resumen Cta Cte"),
            "res_model": "dg.resumen.cta.cte.summary",
            "view_mode": "list,form",
            "domain": [("wizard_id", "=", self.id)],
            "context": {"search_default_group_by_partner": 0},
            "target": "current",
        }
