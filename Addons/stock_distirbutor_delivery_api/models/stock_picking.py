# stock_distirbutor_delivery_api/models/stock_picking.py
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_distributor_delivery = fields.Boolean(
        string="Entrega vía distribuidor",
        help="Si está activo, este remito aparecerá en la app del distribuidor.",
        default=False,
    )

    final_customer_name = fields.Char(
        string="Nombre cliente final",
        help="Nombre o razón social del cliente final informado por el distribuidor.",
    )
    final_customer_street = fields.Char(
        string="Calle y número cliente final",
    )
    final_customer_city = fields.Char(
        string="Localidad cliente final",
    )
    final_customer_vat = fields.Char(
        string="CUIT / DNI cliente final",
    )
    final_customer_phone = fields.Char(
        string="Teléfono cliente final",
    )
    final_customer_email = fields.Char(
        string="Email cliente final",
    )
    final_customer_notes = fields.Text(
        string="Notas cliente final",
    )
    final_customer_completed = fields.Boolean(
        string="Datos cliente final completos",
        help="Marcado cuando el distribuidor cargó los datos del cliente final desde la app.",
        default=False,
    )
