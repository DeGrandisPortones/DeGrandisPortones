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
        """Habilita financiación solo para pricelists permitidas.

        Se controla por parámetro del sistema: dflex_sale_financing.allowed_pricelist_ids
        Valor esperado: lista separada por comas de IDs (ej: '2,5,8').
        """
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

    @api.onchange("financing_plan_id")
    def _onchange_financing_plan_id(self):
        for order in self:
            if not order.financing_plan_id:
                order.financing_card_type = False
                order.financing_rate_id = False
            else:
                order.financing_card_type = False
                order.financing_rate_id = False

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
            order._recompute_financing_prices()

    def _recompute_financing_prices(self):
        """Recalcula el precio unitario desde el precio base de la lista."""
        for order in self:
            rate = order.financing_rate_id.rate_percent if order.financing_rate_id else 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                line._apply_financing_rate(rate)

    def _get_financing_base_unit_for_line(self, line):
        self.ensure_one()
        if self.financing_rate_id:
            return line.financing_base_price_unit
        return line._get_pricelist_display_price()

    def _get_financing_amounts_for_rate_percent(self, rate_percent):
        """Devuelve importes de la orden con un recargo porcentual determinado.

        Se usa para la comparativa del PDF, calculando el total final que vería el cliente.
        """
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

            existing_rate_ids = set(order.financing_comparison_line_ids.mapped("rate_id").ids)
            new_lines = []
            for rate in plan.rate_ids.filtered(lambda rate: rate.active).sorted(key=lambda rate: (rate.card_type, rate.installments)):
                if rate.id in existing_rate_ids:
                    continue
                new_lines.append(
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
            if new_lines:
                order.write({"financing_comparison_line_ids": new_lines})
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

            if rate_percent and rate_percent > 0:
                line.discount = 0.0
                line.price_unit = base * (1.0 + (rate_percent / 100.0))
            else:
                line.discount = 0.0
                line.price_unit = base

    @api.onchange("product_id", "product_uom_qty", "product_uom")
    def _onchange_product_reapply_financing(self):
        for line in self:
            if line.order_id and line.order_id.financing_rate_id:
                line.order_id._recompute_financing_prices()


class SaleOrderFinancingOption(models.Model):
    _name = "sale.order.financing.option"
    _description = "Opción de financiación para presupuesto"
    _order = "sequence, id"

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
        string="Cuotas",
        domain="[('active','=',True), ('plan_id','=',plan_id), ('card_type','=',card_type)]",
    )

    installments = fields.Integer(related="rate_id.installments", string="Cuotas", readonly=True, store=True)
    rate_percent = fields.Float(related="rate_id.rate_percent", string="Recargo %", readonly=True, store=True)
    card_type_label = fields.Char(string="Tarjeta", compute="_compute_card_type_label")

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
