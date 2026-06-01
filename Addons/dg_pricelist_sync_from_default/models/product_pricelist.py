# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    dg_sync_enabled = fields.Boolean(
        string="Sincronizar desde lista principal",
        copy=False,
        help="Activa la generacion de precios fijos en esta lista a partir de otra lista principal.",
    )
    dg_sync_from_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista principal",
        copy=False,
        check_company=True,
        help="Lista que se toma como base. Ejemplo: Predeterminada.",
    )
    dg_sync_discount = fields.Float(
        string="Descuento sobre principal (%)",
        default=0.0,
        copy=False,
        help="Ejemplo: 25 significa que esta lista queda con precio de la principal menos 25%.",
    )
    dg_sync_product_scope = fields.Selection(
        [
            ("all_sale_products", "Todos los productos vendibles"),
            ("source_pricelist_items", "Solo productos con reglas en la principal"),
        ],
        string="Productos a actualizar",
        default="all_sale_products",
        required=True,
        copy=False,
    )
    dg_sync_delete_obsolete = fields.Boolean(
        string="Eliminar precios generados obsoletos",
        default=True,
        copy=False,
        help="Elimina de esta lista los items generados por esta sincronizacion cuando el producto ya no corresponde.",
    )
    dg_sync_last_at = fields.Datetime(
        string="Ultima sincronizacion",
        readonly=True,
        copy=False,
    )
    dg_sync_item_count = fields.Integer(
        string="Items generados",
        readonly=True,
        copy=False,
    )

    @api.constrains(
        "dg_sync_enabled",
        "dg_sync_from_pricelist_id",
        "dg_sync_discount",
    )
    def _check_dg_pricelist_sync_config(self):
        for pricelist in self:
            if not pricelist.dg_sync_enabled:
                continue
            if not pricelist.dg_sync_from_pricelist_id:
                raise ValidationError(_("Debe seleccionar la lista principal."))
            if pricelist.dg_sync_from_pricelist_id == pricelist:
                raise ValidationError(_("Una lista no puede sincronizarse desde si misma."))
            if pricelist.dg_sync_discount < 0 or pricelist.dg_sync_discount > 100:
                raise ValidationError(_("El descuento debe estar entre 0 y 100."))
            pricelist._dg_check_sync_cycle()

    def _dg_check_sync_cycle(self):
        for pricelist in self:
            seen = pricelist
            current = pricelist.dg_sync_from_pricelist_id
            while current and current.dg_sync_enabled:
                if current in seen:
                    raise ValidationError(_("La configuracion genera un ciclo entre listas de precios."))
                seen |= current
                current = current.dg_sync_from_pricelist_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        to_sync = records.filtered("dg_sync_enabled")
        if to_sync and not self.env.context.get("dg_skip_pricelist_sync"):
            to_sync._dg_sync_prices_from_source()
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {
            "dg_sync_enabled",
            "dg_sync_from_pricelist_id",
            "dg_sync_discount",
            "dg_sync_product_scope",
            "dg_sync_delete_obsolete",
        }
        if sync_fields & set(vals) and not self.env.context.get("dg_skip_pricelist_sync"):
            self.filtered("dg_sync_enabled")._dg_sync_prices_from_source()
        return res

    def action_dg_sync_prices_from_source(self):
        self._dg_sync_prices_from_source()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Listas de precios actualizadas"),
                "message": _("La sincronizacion termino correctamente."),
                "sticky": False,
                "type": "success",
            },
        }

    @api.model
    def _cron_dg_sync_prices_from_source(self):
        self.search([("dg_sync_enabled", "=", True)])._dg_sync_prices_from_source()

    @api.model
    def _dg_sync_dependents_of_pricelists(self, source_pricelists):
        source_pricelists = source_pricelists.exists()
        if not source_pricelists:
            return
        targets = self.search(
            [
                ("dg_sync_enabled", "=", True),
                ("dg_sync_from_pricelist_id", "in", source_pricelists.ids),
            ]
        )
        targets._dg_sync_prices_from_source()

    def _dg_sync_prices_from_source(self):
        for pricelist in self.filtered("dg_sync_enabled"):
            pricelist._dg_sync_one_pricelist()

    def _dg_sync_one_pricelist(self):
        self.ensure_one()
        source = self.dg_sync_from_pricelist_id
        if not source:
            return

        products = self._dg_sync_get_products(source)
        generated_items = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", self.id),
                ("dg_sync_generated", "=", True),
            ]
        )
        items_by_product = {
            item.product_id.id: item
            for item in generated_items
            if item.product_id
        }
        product_ids = set(products.ids)

        for product in products:
            price = self._dg_sync_get_target_price(source, product)
            vals = self._dg_sync_item_vals(product, price, source)
            item = items_by_product.get(product.id)
            if item:
                item.with_context(dg_skip_pricelist_sync=True).write(vals)
            else:
                self.env["product.pricelist.item"].with_context(
                    dg_skip_pricelist_sync=True
                ).create(vals)

        if self.dg_sync_delete_obsolete:
            obsolete_items = generated_items.filtered(
                lambda item: item.product_id and item.product_id.id not in product_ids
            )
            obsolete_items.with_context(dg_skip_pricelist_sync=True).unlink()

        self.with_context(dg_skip_pricelist_sync=True).write(
            {
                "dg_sync_last_at": fields.Datetime.now(),
                "dg_sync_item_count": len(products),
            }
        )

    def _dg_sync_get_products(self, source):
        self.ensure_one()
        Product = self.env["product.product"]
        base_domain = [("sale_ok", "=", True), ("active", "=", True)]

        if self.dg_sync_product_scope == "all_sale_products":
            return Product.search(base_domain, order="name asc, id asc")

        items = source.item_ids
        if not items:
            return Product.browse()
        if any(item.applied_on == "3_global" for item in items):
            return Product.search(base_domain, order="name asc, id asc")

        products = Product.browse()
        variant_items = items.filtered(lambda item: item.applied_on == "0_product_variant" and item.product_id)
        template_items = items.filtered(lambda item: item.applied_on == "1_product" and item.product_tmpl_id)
        category_items = items.filtered(lambda item: item.applied_on == "2_product_category" and item.categ_id)

        products |= variant_items.mapped("product_id")
        products |= template_items.mapped("product_tmpl_id.product_variant_ids")

        for item in category_items:
            products |= Product.search(base_domain + [("categ_id", "child_of", item.categ_id.id)])

        return products.filtered(lambda product: product.sale_ok and product.active).sorted(key=lambda product: (product.name or "", product.id))

    def _dg_sync_get_target_price(self, source, product):
        self.ensure_one()
        source = source.with_company(self.company_id or self.env.company)
        product = product.with_company(self.company_id or self.env.company)
        quantity = 1.0

        try:
            source_price = source._get_product_price(
                product,
                quantity,
                uom=product.uom_id,
                date=fields.Date.context_today(self),
            )
        except TypeError:
            source_price = source._get_product_price(product, quantity)

        target_price = float(source_price or 0.0) * (1.0 - (self.dg_sync_discount / 100.0))
        currency = self.currency_id or source.currency_id
        return currency.round(target_price) if currency else target_price

    def _dg_sync_item_vals(self, product, price, source):
        self.ensure_one()
        return {
            "pricelist_id": self.id,
            "applied_on": "0_product_variant",
            "product_id": product.id,
            "min_quantity": 0.0,
            "compute_price": "fixed",
            "fixed_price": price,
            "dg_sync_generated": True,
            "dg_sync_source_pricelist_id": source.id,
        }
