# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("pricelist_id", "company_id")
    def _compute_financing_allowed(self):
        super()._compute_financing_allowed()
        for order in self:
            if order.company_id and order.company_id.id == 1 and order.pricelist_id:
                order.financing_allowed = True
