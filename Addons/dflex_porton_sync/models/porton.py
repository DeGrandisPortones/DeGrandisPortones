from odoo import models, fields

class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    # Valor base tomado de la venta (o cargado a mano)
    base_value = fields.Float(string="Valor base")
    # Resultado de aplicar la fórmula JS
    computed_value = fields.Float(string="Valor calculado")
    # Fórmula en JS (usa la variable 'valor' como base_value)
    formula_js = fields.Char(string="Fórmula JS")