# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    dg_sync_generated = fields.Boolean(
        string="Generado por sync DG",
        copy=False,
        index=True,
        readonly=True,
    )
    dg_sync_source_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista principal DG",
        copy=False,
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("dg_skip_pricelist_sync"):
            records._dg_trigger_dependent_pricelist_sync()
        return records

    def write(self, vals):
        source_pricelists = self.mapped("pricelist_id")
        res = super().write(vals)
        watched_fields = {
            "pricelist_id",
            "applied_on",
            "product_id",
            "product_tmpl_id",
            "categ_id",
            "min_quantity",
            "compute_price",
            "fixed_price",
            "percent_price",
            "base",
            "base_pricelist_id",
            "price_discount",
            "price_surcharge",
            "price_round",
            "price_min_margin",
            "price_max_margin",
            "date_start",
            "date_end",
        }
        if watched_fields & set(vals) and not self.env.context.get("dg_skip_pricelist_sync"):
            (source_pricelists | self.mapped("pricelist_id"))._dg_sync_dependents_after_item_change()
        return res

    def unlink(self):
        source_pricelists = self.mapped("pricelist_id")
        res = super().unlink()
        if not self.env.context.get("dg_skip_pricelist_sync"):
            source_pricelists._dg_sync_dependents_after_item_change()
        return res

    def _dg_trigger_dependent_pricelist_sync(self):
        self.mapped("pricelist_id")._dg_sync_dependents_after_item_change()


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _dg_sync_dependents_after_item_change(self):
        if not self:
            return
        self.env["product.pricelist"]._dg_sync_dependents_of_pricelists(self)
