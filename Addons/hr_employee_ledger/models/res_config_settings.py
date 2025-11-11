# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"

    employee_advance_account_a_id = fields.Many2one(
        "account.account", string="Cuenta Anticipos tipo A",
        domain=[("deprecated","=",False)], help="Cuenta destino para anticipos tipo A (p.ej., Anticipos de sueldo)."
    )
    employee_advance_account_b_id = fields.Many2one(
        "account.account", string="Cuenta Anticipos tipo B",
        domain=[("deprecated","=",False)], help="Cuenta destino para anticipos tipo B (p.ej., Alimentos/vales)."
    )
    employee_batch_journal_id = fields.Many2one(
        "account.journal", string="Diario de cierre RRHH",
        domain=[("type","in",("general","cash","bank"))],
        help="Diario donde se generará el asiento mensual agregado (uno por tipo A/B)."
    )

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    employee_advance_account_a_id = fields.Many2one(
        related="company_id.employee_advance_account_a_id", readonly=False
    )
    employee_advance_account_b_id = fields.Many2one(
        related="company_id.employee_advance_account_b_id", readonly=False
    )
    employee_batch_journal_id = fields.Many2one(
        related="company_id.employee_batch_journal_id", readonly=False
    )