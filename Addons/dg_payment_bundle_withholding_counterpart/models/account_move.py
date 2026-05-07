# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    dg_bundle_withholding_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment Bundle Withholding Payment",
        readonly=True,
        copy=False,
        index=True,
    )
