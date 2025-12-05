from odoo import models, fields

class DflexPorton(models.Model):
    _name = "x_dflex.porton"
    _description = "Portón Dflex"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Nombre",
        related="sale_order_id.name",
        store=True,
    )
    base_value = fields.Float(string="Valor base")
    computed_value = fields.Float(string="Valor calculado")
    formula_js = fields.Char(string="Fórmula JS")