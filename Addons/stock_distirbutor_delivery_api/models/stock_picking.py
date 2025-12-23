# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_distributor_delivery = fields.Boolean(
        string="Entrega vía distribuidor",
        default=False,
        help="Si está marcado, el picking entra en el flujo de la app de distribuidor.",
    )
    final_customer_completed = fields.Boolean(
        string="Datos de cliente final cargados",
        default=False,
    )

    final_customer_name = fields.Char(string="Nombre / Razón social (cliente final)")
    final_customer_street = fields.Char(string="Calle y número (cliente final)")
    final_customer_city = fields.Char(string="Localidad (cliente final)")
    final_customer_vat = fields.Char(string="CUIT / DNI (cliente final)")
    final_customer_phone = fields.Char(string="Teléfono (cliente final)")
    final_customer_email = fields.Char(string="Email (cliente final)")
    final_customer_notes = fields.Text(string="Notas (cliente final)")
