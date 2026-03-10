# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    financing_plan_id = fields.Many2one(
        "sale.financing.plan",
        string="Plan de financiación",
        domain="[('active', '=', True), ('company_id', 'in', (company_id, False))]",
        copy=False,
    )
    financing_card_type = fields.Selection(
        selection=lambda self: self.env["sale.financing.rate"]._fields["card_type"].selection,
        string="Tarjeta",
        copy=False,
    )
    financing_rate_id = fields.Many2one(
        "sale.financing.rate",
        string="Cuotas",
        domain="[('active','=',True), ('plan_id','=',financing_plan_id), ('card_type','=',financing_card_type)]",
        copy=False,
    )
    financing_rate_percent = fields.Float(related="financing_rate_id.rate_percent", string="Recargo %", readonly=True)

    financing_allowed = fields.Boolean(string="Financiación habilitada", compute="_compute_financing_allowed")
    financing_comparison_line_ids = fields.One2many(
        "sale.order.financing.option",
        "order_id",
        string="Opciones de comparativa",
        copy=True,
    )

    @api.depends("pricelist_id")
    def _compute_financing_allowed(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "dflex_sale_financing.allowed_pricelist_ids", default=""
        )
        allowed_ids = set()
        for token in (param or "").split(","):
            token = (token or "").strip()
            if not token:
                continue
            try:
                allowed_ids.add(int(token))
            except ValueError:
                continue
        for order in self:
            order.financing_allowed = bool(order.pricelist_id and order.pricelist_id.id in allowed_ids)

    def _prepare_financing_comparison_line_commands(self, plan):
        commands = [(5, 0, 0)]
        for rate in plan.rate_ids.filtered(lambda rate: rate.active).sorted(key=lambda rate: (rate.card_type, rate.installments)):
            commands.append(
                (
                    0,
                    0,
                    {
                        "plan_id": plan.id,
                        "card_type": rate.card_type,
                        "rate_id": rate.id,
                        "include_in_report": True,
                        "sequence": 10,
                    },
                )
            )
        return commands

    @api.onchange("financing_plan_id")
    def _onchange_financing_plan_id(self):
        for order in self:
            order.financing_card_type = False
            order.financing_rate_id = False
            if order.financing_plan_id:
                order.financing_comparison_line_ids = order._prepare_financing_comparison_line_commands(order.financing_plan_id)
            else:
                order.financing_comparison_line_ids = [(5, 0, 0)]

    @api.onchange("financing_card_type")
    def _onchange_financing_card_type(self):
        for order in self:
            order.financing_rate_id = False

    @api.onchange("financing_rate_id", "pricelist_id")
    def _onchange_financing_rate_or_pricelist(self):
        for order in self:
            if not order.financing_allowed:
                order.financing_plan_id = False
                order.financing_card_type = False
                order.financing_rate_id = False
                order.financing_comparison_line_ids = [(5, 0, 0)]
            order._recompute_financing_prices()

    def _recompute_financing_prices(self):
        for order in self:
            rate = order.financing_rate_id.rate_percent if order.financing_rate_id else 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                line._apply_financing_rate(rate)

    def _get_financing_base_unit_for_line(self, line):
        self.ensure_one()
        return line.financing_base_price_unit or line._get_pricelist_display_price()

    def _get_financing_amounts_for_rate_percent(self, rate_percent):
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_invoice_id or self.partner_id
        untaxed_total = 0.0
        total = 0.0
        for line in self.order_line.filtered(lambda l: not l.display_type and l.product_id):
            base_unit = self._get_financing_base_unit_for_line(line)
            unit_price = base_unit * (1.0 + ((rate_percent or 0.0) / 100.0))
            taxes_res = line.tax_id.compute_all(
                unit_price,
                currency=self.currency_id,
                quantity=line.product_uom_qty,
                product=line.product_id,
                partner=partner,
            )
            untaxed_total += taxes_res["total_excluded"]
            total += taxes_res["total_included"]
        return {
            "untaxed_total": untaxed_total,
            "total": total,
        }

    def _get_financing_comparison_report_lines(self):
        self.ensure_one()
        return self.financing_comparison_line_ids.filtered(lambda line: line.include_in_report and line.rate_id).sorted(
            key=lambda line: (line.sequence, line.card_type or "", line.installments or 0, line.id)
        )

    def action_sync_financing_comparison_lines(self):
        for order in self:
            plan = order.financing_plan_id or self.env["sale.financing.plan"].search(
                [
                    ("active", "=", True),
                    ("company_id", "in", [order.company_id.id, False]),
                ],
                limit=1,
                order="id asc",
            )
            if not plan:
                raise UserError(_("No hay un plan de financiación activo para cargar la comparativa."))

            if not order.financing_plan_id:
                order.financing_plan_id = plan

            order.financing_comparison_line_ids = order._prepare_financing_comparison_line_commands(plan)
        return True

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {"financing_plan_id", "financing_card_type", "financing_rate_id", "pricelist_id", "order_line"}
        if trigger_fields.intersection(vals.keys()) and not self.env.context.get("skip_financing_recompute"):
            for order in self:
                order.with_context(skip_financing_recompute=True)._recompute_financing_prices()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    financing_base_price_unit = fields.Float(
        string="Precio base (sin recargo)",
        readonly=True,
        copy=False,
        help="Precio calculado por lista de precios antes de aplicar recargo por financiación.",
    )

    def _get_pricelist_display_price(self):
        self.ensure_one()
        if not self.order_id.pricelist_id:
            return self.product_id.lst_price
        return self._get_display_price()

    def _apply_financing_rate(self, rate_percent):
        for line in self:
            if line.display_type or not line.product_id:
                continue

            base = line._get_pricelist_display_price()
            line.financing_base_price_unit = base
            line.discount = 0.0
            line.price_unit = base * (1.0 + ((rate_percent or 0.0) / 100.0)) if rate_percent else base

    @api.onchange("product_id", "product_uom_qty", "product_uom")
    def _onchange_product_reapply_financing(self):
        for line in self:
            if line.order_id:
                line.order_id._recompute_financing_prices()
