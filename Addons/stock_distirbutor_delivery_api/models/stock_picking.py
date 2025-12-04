# stock_distributor_delivery_api/models/stock_picking.py
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Copiamos la marca del pedido de venta
    is_distributor_delivery = fields.Boolean(
        string="Entrega vía distribuidor",
        related="sale_id.is_distributor_delivery",
        store=True,
        readonly=True,
    )

    final_customer_name = fields.Char(
        string="Final Customer Name",
    )
    final_customer_street = fields.Char(
        string="Final Customer Street",
    )
    final_customer_city = fields.Char(
        string="Final Customer City",
    )
    final_customer_vat = fields.Char(
        string="Final Customer VAT / CUIT/DNI",
    )
    final_customer_phone = fields.Char(
        string="Final Customer Phone",
    )
    final_customer_notes = fields.Text(
        string="Final Customer Notes",
    )

    final_customer_completed = fields.Boolean(
        string="Final Customer Data Completed",
        default=False,
    )
