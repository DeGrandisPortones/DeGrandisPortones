from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    distributor_available = fields.Boolean(
        string="Disponible para app distribuidor",
        default=False,
        help="Si está marcado, el producto aparece en el pseudo-presupuestador.",
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    distributor_customer = fields.Boolean(
        string="Cliente app distribuidor",
        help="Si está marcado, este partner puede seleccionarse como cliente en la app del distribuidor.",
    )
