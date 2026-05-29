from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class DgAccountStatementWizard(models.TransientModel):
    _name = "dg.account.statement.wizard"
    _description = "Resumen Cta Cte"

    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta", default=fields.Date.context_today, required=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        help="Cliente para el que se quiere ver e imprimir la cuenta corriente.",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Clientes",
        help="Campo de compatibilidad con versiones anteriores. Usar Cliente.",
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

    def _get_effective_partner(self):
        self.ensure_one()
        partner = self.partner_id or (self.partner_ids[:1] if self.partner_ids else False)
        if not partner:
            raise UserError(_("Debe seleccionar un cliente."))
        return partner.commercial_partner_id

    def action_print_pdf(self):
        self.ensure_one()
        self._check_dates()
        if not self.company_id:
            raise UserError(_("Debe seleccionar una empresa."))
        self._get_effective_partner()
        return self.env.ref("dg_resumen_cta_cte.action_report_dg_account_statement").report_action(self)

    def _line_base_vals(self, statement):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "company_id": self.company_id.id,
            "partner_id": statement["partner"].id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "include_initial_balance": self.include_initial_balance,
            "currency_id": statement["currency"].id,
        }

    def action_view_detail(self):
        self.ensure_one()
        self._check_dates()
        if not self.company_id:
            raise UserError(_("Debe seleccionar una empresa."))
        self._get_effective_partner()

        old_lines = self.env["dg.resumen.cta.cte.line"].search([("wizard_id", "=", self.id)])
        old_lines.unlink()

        report = self.env["report.dg_resumen_cta_cte.report_account_statement"]
        statements = report._get_wizard_statements(self)
        vals_list = []
        sequence = 10

        for statement in statements:
            base_vals = self._line_base_vals(statement)
            for group in statement["groups"]:
                for line in group["lines"]:
                    vals = dict(base_vals)
                    vals.update(
                        {
                            "sequence": sequence,
                            "report_group": group["key"],
                            "display_type": "line",
                            "date": line["date"],
                            "document": line["document"],
                            "description": line.get("description") or "",
                            "debit": line["debit"],
                            "credit": line["credit"],
                            "balance": line["balance"],
                        }
                    )
                    vals_list.append(vals)
                    sequence += 10

                vals = dict(base_vals)
                vals.update(
                    {
                        "sequence": sequence,
                        "report_group": group["key"],
                        "display_type": "subtotal",
                        "document": group["label"],
                        "debit": group["debit"],
                        "credit": group["credit"],
                        "balance": group["balance"],
                    }
                )
                vals_list.append(vals)
                sequence += 10

            vals = dict(base_vals)
            vals.update(
                {
                    "sequence": sequence,
                    "report_group": "total",
                    "display_type": "total",
                    "document": _("Total"),
                    "balance": statement["total_balance"],
                }
            )
            vals_list.append(vals)
            sequence += 10

        if vals_list:
            self.env["dg.resumen.cta.cte.line"].create(vals_list)

        return {
            "type": "ir.actions.act_window",
            "name": _("Resumen de cuenta corriente"),
            "res_model": "dg.resumen.cta.cte.line",
            "view_mode": "list,form",
            "domain": [("wizard_id", "=", self.id)],
            "context": {
                "search_default_group_by_report_group": 1,
                "create": False,
                "edit": False,
                "delete": False,
            },
            "target": "current",
        }

    def action_view_summary(self):
        # Compatibilidad con el boton de la version anterior, si quedara en cache.
        return self.action_view_detail()
