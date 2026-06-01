# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {"list_price", "sale_ok", "active", "categ_id"}
        if watched_fields & set(vals) and not self.env.context.get("dg_skip_pricelist_sync"):
            self.env["product.pricelist"].search(
                [("dg_sync_enabled", "=", True)]
            )._dg_sync_prices_from_source()
        return res
