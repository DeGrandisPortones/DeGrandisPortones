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
        help="Dejar vacio para imprimir clientes con movimientos en el rango seleccionado.",
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
