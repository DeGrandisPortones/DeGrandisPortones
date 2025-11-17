
# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"
    employee_advance_account_a_id = fields.Many2one("account.account", string="Cuenta Anticipos tipo A", domain=[("deprecated","=",False)])
    employee_advance_account_b_id = fields.Many2one("account.account", string="Cuenta Anticipos tipo B", domain=[("deprecated","=",False)])
    employee_batch_journal_id = fields.Many2one("account.journal", string="Diario de cierre RRHH", domain=[("type","in",("general","cash","bank"))])

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    employee_advance_account_a_id = fields.Many2one(related="company_id.employee_advance_account_a_id", readonly=False)
    employee_advance_account_b_id = fields.Many2one(related="company_id.employee_advance_account_b_id", readonly=False)
    employee_batch_journal_id = fields.Many2one(related="company_id.employee_batch_journal_id", readonly=False)
