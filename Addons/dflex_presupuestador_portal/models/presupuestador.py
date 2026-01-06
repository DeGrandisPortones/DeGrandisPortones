# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PresupuestadorRubro(models.Model):
    _name = "presupuestador.rubro"
    _description = "Rubro de Presupuestador"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    qty_mode = fields.Selection(
        [
            ("m2", "m² (ancho x alto)"),
            ("one", "1 unidad"),
            ("manual", "Manual"),
        ],
        required=True,
        default="manual",
    )
    product_category_id = fields.Many2one("product.category", string="Categoría de Productos (opcional)")
    active = fields.Boolean(default=True)


class PresupuestadorPedido(models.Model):
    _name = "presupuestador.pedido"
    _description = "Pedido de Presupuesto (Portal)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(default=lambda self: _("Presupuesto"), readonly=True, copy=False, tracking=True)
    state = fields.Selection(
        [("draft", "Borrador"), ("sent", "Enviado"), ("done", "Aprobado"), ("cancel", "Cancelado")],
        default="draft",
        tracking=True,
    )

    partner_id = fields.Many2one("res.partner", string="Cliente / Distribuidor", required=True, tracking=True)
    pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios", required=True, tracking=True)
    coeficiente = fields.Float(string="Coeficiente (%)", default=25.0, tracking=True)

    sistema = fields.Char(string="Sistema")
    ancho = fields.Float(string="Ancho (m)")
    alto = fields.Float(string="Alto (m)")
    peso_m2 = fields.Float(string="Peso (kg/m²)")

    m2 = fields.Float(string="m²", compute="_compute_derived", store=True)
    peso_total = fields.Float(string="Peso total (kg)", compute="_compute_derived", store=True)

    line_ids = fields.One2many("presupuestador.linea", "pedido_id", string="Líneas")

    amount_untaxed = fields.Monetary(string="Subtotal", compute="_compute_amounts", store=True)
    amount_tax = fields.Monetary(string="IVA", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(string="Total", compute="_compute_amounts", store=True)
    currency_id = fields.Many2one("res.currency", related="pricelist_id.currency_id", store=True, readonly=True)

    @api.depends("ancho", "alto", "peso_m2")
    def _compute_derived(self):
        for rec in self:
            rec.m2 = (rec.ancho or 0.0) * (rec.alto or 0.0)
            rec.peso_total = (rec.m2 or 0.0) * (rec.peso_m2 or 0.0)

    @api.depends("line_ids.price_subtotal", "line_ids.price_tax", "line_ids.price_total")
    def _compute_amounts(self):
        for rec in self:
            rec.amount_untaxed = sum(rec.line_ids.mapped("price_subtotal"))
            rec.amount_tax = sum(rec.line_ids.mapped("price_tax"))
            rec.amount_total = sum(rec.line_ids.mapped("price_total"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("Presupuesto"):
                vals["name"] = self.env["ir.sequence"].next_by_code("presupuestador.pedido") or _("Presupuesto")
        return super().create(vals_list)


class PresupuestadorLinea(models.Model):
    _name = "presupuestador.linea"
    _description = "Línea de Presupuestador"
    _order = "id"

    pedido_id = fields.Many2one("presupuestador.pedido", required=True, ondelete="cascade")
    rubro_id = fields.Many2one("presupuestador.rubro", required=True)
    product_id = fields.Many2one("product.product", required=True)

    qty = fields.Float(string="Cantidad", default=1.0)
    obs = fields.Char(string="Observación")

    precio_distr = fields.Monetary(string="Precio Distr.", currency_field="currency_id", readonly=True)
    price_unit = fields.Monetary(string="Precio", currency_field="currency_id", readonly=True)

    tax_ids = fields.Many2many("account.tax", string="Impuestos", domain=[("type_tax_use", "in", ("sale", "none"))])
    currency_id = fields.Many2one("res.currency", related="pedido_id.currency_id", store=True, readonly=True)

    price_subtotal = fields.Monetary(string="Subtotal", currency_field="currency_id", compute="_compute_amount_line", store=True)
    price_tax = fields.Monetary(string="IVA", currency_field="currency_id", compute="_compute_amount_line", store=True)
    price_total = fields.Monetary(string="Total", currency_field="currency_id", compute="_compute_amount_line", store=True)

    @api.depends("qty", "price_unit", "tax_ids")
    def _compute_amount_line(self):
        for line in self:
            subtotal = (line.price_unit or 0.0) * (line.qty or 0.0)
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line.price_unit or 0.0,
                    currency=line.currency_id,
                    quantity=line.qty or 0.0,
                    product=line.product_id,
                    partner=line.pedido_id.partner_id,
                )
                line.price_subtotal = taxes_res.get("total_excluded", subtotal)
                line.price_total = taxes_res.get("total_included", subtotal)
                line.price_tax = line.price_total - line.price_subtotal
            else:
                line.price_subtotal = subtotal
                line.price_tax = 0.0
                line.price_total = subtotal

    def _get_pricelist_price(self):
        self.ensure_one()
        pl = self.pedido_id.pricelist_id
        partner = self.pedido_id.partner_id
        product = self.product_id
        qty = self.qty or 1.0

        price = None
        if hasattr(pl, "_get_product_price"):
            try:
                price = pl._get_product_price(product, qty, partner)
            except Exception:
                price = None
        if price is None and hasattr(pl, "get_product_price"):
            try:
                price = pl.get_product_price(product, qty, partner)
            except Exception:
                price = None
        if price is None and hasattr(pl, "get_product_price_rule"):
            try:
                price, _rule_id = pl.get_product_price_rule(product, qty, partner)
            except Exception:
                price = None
        if price is None:
            price = product.lst_price
        return price

    def recompute_prices(self):
        for line in self:
            base = line._get_pricelist_price()
            line.precio_distr = base
            coef = line.pedido_id.coeficiente or 0.0
            line.price_unit = base * (1.0 + (coef / 100.0))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.recompute_prices()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("qty", "product_id", "tax_ids")):
            self.recompute_prices()
        return res
