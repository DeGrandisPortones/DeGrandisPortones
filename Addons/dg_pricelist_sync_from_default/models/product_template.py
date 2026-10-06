# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    dg_keep_same_price_all_pricelists = fields.Boolean(
        string="Mismo precio en todas las listas",
        default=False,
        tracking=True,
        help="Las listas sincronizadas desde la lista principal toman el precio de la principal "
        "sin aplicar su descuento.",
    )

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {"list_price", "sale_ok", "active", "categ_id", "dg_keep_same_price_all_pricelists"}
        if watched_fields & set(vals) and not self.env.context.get("dg_skip_pricelist_sync"):
            self.env["product.pricelist"].search(
                [("dg_sync_enabled", "=", True)]
            )._dg_sync_prices_from_source()
        return res
