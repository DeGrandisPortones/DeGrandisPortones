from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Related a partner_id.category_id (Tags de la ficha de contacto).
    # store=True para poder usarlo en filtros y "Agrupar por" desde la
    # búsqueda de Facturación. No depende de la compañía: aplica igual
    # para todas las empresas de la base (Dflex, Vert, etc.).
    # Un related Many2many con store=True necesita declarar la tabla de
    # relación a mano: Odoo no la auto-genera para campos related/computed
    # (si se omite, falla el _auto_init con "NoneType has no isidentifier").
    partner_category_id = fields.Many2many(
        comodel_name="res.partner.category",
        related="partner_id.category_id",
        string="Etiquetas de Cliente",
        relation="account_move_res_partner_category_rel",
        column1="account_move_id",
        column2="category_id",
        store=True,
    )
