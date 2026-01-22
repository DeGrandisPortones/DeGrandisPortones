# -*- coding: utf-8 -*-
from odoo import api, fields, models

CARD_TYPE_SELECTION = [
    ("cordobesa", "Tarjeta Cordobesa"),
    ("naranja", "Tarjeta Naranja"),
    ("otras", "Otras tarjetas bancarizadas"),
]


class SaleFinancingPlan(models.Model):
    _name = "sale.financing.plan"
    _description = "Plan de financiación (recargos por cuotas)"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, index=True)

    rate_ids = fields.One2many("sale.financing.rate", "plan_id", string="Tarifas")


class SaleFinancingRate(models.Model):
    _name = "sale.financing.rate"
    _description = "Recargo por tarjeta/cuotas"
    _order = "card_type, installments"

    plan_id = fields.Many2one("sale.financing.plan", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="plan_id.company_id", store=True, index=True)

    card_type = fields.Selection(CARD_TYPE_SELECTION, required=True, index=True)
    installments = fields.Integer(required=True, index=True, help="Cantidad de cuotas")
    rate_percent = fields.Float(
        required=True,
        digits=(16, 2),
        help="Porcentaje de recargo (ej: 25.00 = +25%)",
    )
    active = fields.Boolean(default=True)

    name = fields.Char(compute="_compute_name", store=True)

    _sql_constraints = [
        ("uniq_rate", "unique(plan_id, card_type, installments)", "Ya existe una tarifa para ese plan/tarjeta/cuotas."),
    ]

    @api.depends("plan_id.name", "card_type", "installments", "rate_percent")
    def _compute_name(self):
        for rec in self:
            card = dict(CARD_TYPE_SELECTION).get(rec.card_type, rec.card_type or "")
            rec.name = f"{card} - {rec.installments} cuotas (+{rec.rate_percent:.2f}%)"
