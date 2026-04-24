from odoo import fields, models


class L10nLatamCheckHistoryWizard(models.TransientModel):
    _name = "l10n_latam.check.history.wizard"
    _description = "Historial del cheque"

    check_id = fields.Many2one(
        comodel_name="l10n_latam.check",
        string="Cheque",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="l10n_latam.check.history.line",
        inverse_name="wizard_id",
        string="Movimientos",
        readonly=True,
    )


class L10nLatamCheckHistoryLine(models.TransientModel):
    _name = "l10n_latam.check.history.line"
    _description = "Línea historial del cheque"
    _order = "destination_movement_date, id"

    wizard_id = fields.Many2one(
        comodel_name="l10n_latam.check.history.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    check_id = fields.Many2one(
        comodel_name="l10n_latam.check",
        string="Cheque",
        readonly=True,
    )
    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Movimiento",
        readonly=True,
    )
    issue_date = fields.Date(string="Fecha emisión", readonly=True)
    issuer_vat = fields.Char(string="CUIT emisor", readonly=True)
    issuer_name = fields.Char(string="Razón social emisor", readonly=True)
    payment_date = fields.Date(string="Fecha de pago", readonly=True)
    payment_contact_name = fields.Char(string="Contacto que hizo el pago", readonly=True)
    payment_contact_vat = fields.Char(string="CUIT contacto pago", readonly=True)
    destination_type = fields.Char(string="Tipo destino", readonly=True)
    destination = fields.Char(string="Destino del cheque", readonly=True)
    destination_movement_date = fields.Datetime(string="Fecha mov. destino", readonly=True)
