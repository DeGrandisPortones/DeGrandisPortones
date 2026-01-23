from odoo import api, fields, models

class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    # Nota:
    # Este módulo extiende un modelo creado por Studio (x_dflex.porton).
    # Por compatibilidad con vistas/wizard existentes, se mantienen los nombres x_*.

    # Valor base tomado de la venta (o cargado a mano)
    x_base_value = fields.Float(string="Valor base")
    # Resultado de aplicar la fórmula JS
    x_computed_value = fields.Float(string="Valor calculado")
    # Fórmula en JS (usa la variable 'valor' como base)
    x_formula_js = fields.Char(string="Fórmula JS")

    # Alias compatible con versiones previas del módulo:
    # la relación real suele llamarse sale_order_id (creada en Studio).
    # La vista y el wizard referencian x_studio_sale_order_id.
    x_studio_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Cotización Odoo",
        compute="_compute_x_studio_sale_order_id",
        inverse="_inverse_x_studio_sale_order_id",
        store=True,
    )

    @api.depends("sale_order_id")
    def _compute_x_studio_sale_order_id(self):
        for rec in self:
            rec.x_studio_sale_order_id = rec.sale_order_id

    def _inverse_x_studio_sale_order_id(self):
        for rec in self:
            rec.sale_order_id = rec.x_studio_sale_order_id