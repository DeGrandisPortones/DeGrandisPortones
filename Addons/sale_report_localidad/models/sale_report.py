from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    partner_city = fields.Char(string='Localidad', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['partner_city'] = 'partner.city'
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += ', partner.city'
        return res
