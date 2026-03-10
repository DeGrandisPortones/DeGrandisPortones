# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderFinancingOption(models.Model):
    _name = "sale.order.financing.option"
    _description = "Opción de financiación para presupuesto"
    _order = "sequence, id"
    _table = "sale_order_financing_option"

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="order_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="order_id.currency_id", store=True)

    include_in_report = fields.Boolean(string="Imprimir", default=True)
    plan_id = fields.Many2one(
        "sale.financing.plan",
        string="Plan",
        domain="[('active', '=', True), ('company_id', 'in', (company_id, False))]",
    )
    card_type = fields.Selection(
        selection=lambda self: self.env["sale.financing.rate"]._fields["card_type"].selection,
        string="Tarjeta",
    )
    rate_id = fields.Many2one(
        "sale.financing.rate",
        string="Opción",
        domain="[('active','=',True), ('plan_id','=',plan_id), ('card_type','=',card_type)]",
    )

    installments = fields.Integer(related="rate_id.installments", string="Cant. cuotas", readonly=True, store=True)
    rate_percent = fields.Float(related="rate_id.rate_percent", string="Recargo %", readonly=True, store=True)
    card_type_label = fields.Char(string="Tarjeta texto", compute="_compute_card_type_label")

    base_total = fields.Monetary(string="Total contado", compute="_compute_amounts")
    financed_total = fields.Monetary(string="Total financiado", compute="_compute_amounts")
    installment_amount = fields.Monetary(string="Valor cuota", compute="_compute_amounts")

    @api.depends("card_type")
    def _compute_card_type_label(self):
        selection = dict(self.env["sale.financing.rate"]._fields["card_type"].selection)
        for line in self:
            line.card_type_label = selection.get(line.card_type, "")

    @api.depends(
        "rate_id",
        "rate_percent",
        "installments",
        "order_id.order_line",
        "order_id.order_line.tax_id",
        "order_id.order_line.product_uom_qty",
        "order_id.order_line.financing_base_price_unit",
        "order_id.order_line.price_unit",
        "order_id.currency_id",
    )
    def _compute_amounts(self):
        for line in self:
            if not line.order_id or not line.rate_id:
                line.base_total = 0.0
                line.financed_total = 0.0
                line.installment_amount = 0.0
                continue
            base_amounts = line.order_id._get_financing_amounts_for_rate_percent(0.0)
            financed_amounts = line.order_id._get_financing_amounts_for_rate_percent(line.rate_percent or 0.0)
            line.base_total = base_amounts["total"]
            line.financed_total = financed_amounts["total"]
            line.installment_amount = (line.financed_total / line.installments) if line.installments else 0.0

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        for line in self:
            line.card_type = False
            line.rate_id = False

    @api.onchange("card_type")
    def _onchange_card_type(self):
        for line in self:
            line.rate_id = False

    @api.onchange("rate_id")
    def _onchange_rate_id(self):
        for line in self:
            if line.rate_id:
                line.plan_id = line.rate_id.plan_id
                line.card_type = line.rate_id.card_type
