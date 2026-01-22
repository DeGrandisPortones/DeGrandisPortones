# -*- coding: utf-8 -*-
from odoo import api, fields, models
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
                # Ignorar basura en el parámetro
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
                # Si cambia plan, limpiar selección dependiente
                order.financing_card_type = False
                order.financing_rate_id = False

    @api.onchange("financing_card_type")
    def _onchange_financing_card_type(self):
        for order in self:
            order.financing_rate_id = False

    @api.onchange("financing_rate_id", "pricelist_id")
    def _onchange_financing_rate_or_pricelist(self):
        for order in self:
            # Si la lista no habilita financiación, limpiar selección y recalcular sin recargo
            if not order.financing_allowed:
                order.financing_plan_id = False
                order.financing_card_type = False
                order.financing_rate_id = False
            order._recompute_financing_prices()

    def _recompute_financing_prices(self):
        """Recalcula el precio unitario de cada línea en función de:
        - precio resultante de la lista de precios (display price)
        - recargo por financiación (si aplica)

        Nota: para evitar aplicar recargos múltiples, se recalcula desde base cada vez.
        """
        for order in self:
            rate = order.financing_rate_id.rate_percent if order.financing_rate_id else 0.0
            # Recalcular únicamente líneas de producto (no secciones/notas)
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                line._apply_financing_rate(rate)

    def write(self, vals):
        res = super().write(vals)
        # Recalcular al guardar si cambian campos relevantes
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
        """Obtiene el precio unitario que Odoo mostraría para el producto según la lista de precios."""
        self.ensure_one()
        if not self.order_id.pricelist_id:
            return self.product_id.lst_price
        # _get_display_price suele ser el método estándar en sale.order.line
        return self._get_display_price()

    def _apply_financing_rate(self, rate_percent):
        """Aplica recargo al precio unitario de la línea, recalculando desde precio base de lista."""
        for line in self:
            if line.display_type or not line.product_id:
                continue

            base = line._get_pricelist_display_price()
            line.financing_base_price_unit = base

            if rate_percent and rate_percent > 0:
                # Para evitar doble descuento (si la pricelist usa discount policy), fijamos descuento en 0
                line.discount = 0.0
                line.price_unit = base * (1.0 + (rate_percent / 100.0))
            else:
                # Sin financiación: dejamos el precio neto por lista y descuento en 0 para coherencia
                line.discount = 0.0
                line.price_unit = base

    @api.onchange("product_id", "product_uom_qty", "product_uom")
    def _onchange_product_reapply_financing(self):
        for line in self:
            if line.order_id and line.order_id.financing_rate_id:
                line.order_id._recompute_financing_prices()