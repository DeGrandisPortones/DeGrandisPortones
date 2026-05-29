from odoo import _, fields, models
from odoo.exceptions import UserError


class DgResumenCtaCteLine(models.TransientModel):
    _name = "dg.resumen.cta.cte.line"
    _description = "Resumen Cta Cte - Detalle"
    _order = "sequence, id"

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
    sequence = fields.Integer(string="Secuencia", readonly=True, default=10)
    report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
            ("total", "Total"),
        ],
        string="Cuenta",
        readonly=True,
    )
    display_type = fields.Selection(
        selection=[
            ("line", "Movimiento"),
            ("subtotal", "Subtotal"),
            ("total", "Total"),
        ],
        string="Tipo de linea",
        readonly=True,
        default="line",
    )
    date = fields.Date(string="Fecha", readonly=True)
    document = fields.Char(string="Documento", readonly=True)
    description = fields.Char(string="Descripcion", readonly=True)
    entry_type = fields.Selection(
        selection=[
            ("sale", "Venta"),
            ("collection", "Cobranza"),
            ("opening", "Saldo anterior"),
        ],
        string="Tipo",
        readonly=True,
    )
    debit = fields.Monetary(
        string="Debe",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )
    credit = fields.Monetary(
        string="Haber",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )
    balance = fields.Monetary(
        string="Saldo",
        currency_field="currency_id",
        readonly=True,
        group_operator="sum",
    )

    show_download_fca = fields.Boolean(string="Mostrar descargar FCA", readonly=True)
    show_download_internas = fields.Boolean(string="Mostrar descargar Internas", readonly=True)
    show_download_all = fields.Boolean(string="Mostrar descargar ambas", readonly=True)

    def _get_single_wizard(self):
        if not self:
            raise UserError(_("Seleccione una linea del resumen."))
        wizards = self.mapped("wizard_id")
        if len(wizards) != 1:
            raise UserError(_("Seleccione lineas del mismo resumen."))
        return wizards

    def _download_with_group(self, print_group):
        wizard = self._get_single_wizard()
        wizard.write({"print_group": print_group})
        return wizard.action_print_pdf()

    def action_download_resumen(self):
        return self._download_with_group("all")

    def action_download_all(self):
        return self._download_with_group("all")

    def action_download_fca(self):
        return self._download_with_group("fca")

    def action_download_internas(self):
        return self._download_with_group("internas")
