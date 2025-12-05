from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = "sale.order"

    porton_ids = fields.One2many(
        "x_dflex.porton",
        "sale_order_id",
        string="Portones Dflex",
    )