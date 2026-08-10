from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Related a partner_id.category_id (Tags de la ficha de contacto).
    # store=True para poder usarlo en filtros y "Agrupar por" desde la
    # búsqueda de Facturación. No depende de la compañía: aplica igual
    # para todas las empresas de la base (Dflex, Vert, etc.).
    partner_category_id = fields.Many2many(
        related="partner_id.category_id",
        string="Etiquetas de Cliente",
        store=True,
    )
