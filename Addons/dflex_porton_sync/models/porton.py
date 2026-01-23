from odoo import fields, models

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

    # Relación a la cotización creada en Odoo.
    # Importante: NO dependemos de campos Studio preexistentes (sale_order_id, etc.)
    # porque el modelo x_dflex.porton vive en la BD y puede variar por instancia.
    # Este campo lo crea el módulo y es el que usa el backend (JSON-RPC) para vincular.
    x_studio_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Cotización Odoo",
        ondelete="set null",
        index=True,
    )