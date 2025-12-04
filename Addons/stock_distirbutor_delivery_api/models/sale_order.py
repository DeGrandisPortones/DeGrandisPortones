# stock_distributor_delivery_api/models/sale_order.py
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_distributor_delivery = fields.Boolean(
        string="Entrega vía distribuidor",
        help="Tildar si este pedido será entregado por el distribuidor externo.",
    )
