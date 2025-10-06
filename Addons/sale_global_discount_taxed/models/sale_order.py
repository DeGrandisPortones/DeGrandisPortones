# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    global_discount_rate = fields.Float(
        string="Descuento global (%)",
        help="Porcentaje aplicado a todas las líneas antes del cálculo de impuestos. "
             "Si usás el widget de porcentaje, el valor interno puede ser fracción (0..1).",
        default=0.0,
        digits=(16, 4),
    )
    global_discount_amount = fields.Monetary(
        string="Descuento global (importe)",
        compute="_amount_all",
        store=True,
        currency_field="currency_id",
        help="Importe total descontado sobre la base imponible (antes de impuestos).",
    )

    @api.constrains("global_discount_rate")
    def _check_global_discount_rate(self):
        for order in self:
            v = order.global_discount_rate or 0.0
            # Permitimos 0..1 (fracción) o 0..100 (porcentaje)
            if v < 0.0 or v > 100.0:
                raise ValidationError(
                    "El Descuento global debe estar entre 0 y 100 "
                    "(o 0.0–1.0 si se guarda como fracción)."
                )

    @api.depends(
        "order_line.price_unit",
        "order_line.discount",
        "order_line.product_uom_qty",
        "order_line.tax_id",
        "order_line.display_type",
        "order_line.product_id",
        "currency_id",
        "company_id",
        "partner_id",
        "partner_shipping_id",
        "global_discount_rate",
    )
    def _amount_all(self):
        """
        Aplica descuento global (%) por línea ANTES de impuestos, combinándolo
        con el descuento propio de la línea (multiplicativo).
        """
        for order in self:
            currency = order.currency_id
            partner = order.partner_shipping_id or order.partner_id
            company = order.company_id

            amount_untaxed = 0.0
            amount_tax = 0.0
            discount_base_total = 0.0
            groups = defaultdict(lambda: {'base': 0.0, 'amount': 0.0, 'group': False})

            # --- IMPORTANTE: normalizar el valor del widget percentage ---
            # Si viene 0..1 (fracción) lo usamos así; si viene 0..100 lo pasamos a fracción.
            raw = order.global_discount_rate or 0.0
            global_rate = raw if raw <= 1.0 else (raw / 100.0)

            for line in order.order_line.filtered(lambda l: not l.display_type):
                # En Odoo el descuento de línea es 0..100 -> convertir a fracción
                line_rate = (line.discount or 0.0) / 100.0

                # Factor combinado: (1 - d_linea) * (1 - d_global)
                effective_factor = (1.0 - line_rate) * (1.0 - global_rate)
                eff_price_unit = line.price_unit * effective_factor

                # Cuánto aporta el DESCUENTO GLOBAL (puro) a la base de esta línea
                base_line_line_discount = line.price_unit * (1.0 - line_rate) * line.product_uom_qty
                base_line_both_discounts = eff_price_unit * line.product_uom_qty
                discount_base_total += max(0.0, base_line_line_discount - base_line_both_discounts)

                # Impuestos con precio ya descontado
                taxes_res = line.tax_id.with_context(force_company=company.id).compute_all(
                    eff_price_unit,
                    currency=currency,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=partner,
                )

                amount_untaxed += taxes_res["total_excluded"]
                amount_tax += taxes_res["total_included"] - taxes_res["total_excluded"]

                # Acumular por grupo de impuestos
                for t in taxes_res.get("taxes", []):
                    tax_obj = self.env["account.tax"].browse(t["id"])
                    group = tax_obj.tax_group_id
                    groups[group]["group"] = group
                    groups[group]["amount"] += t["amount"]
                    groups[group]["base"] += t["base"]

            order.amount_untaxed = currency.round(amount_untaxed)
            order.amount_tax = currency.round(amount_tax)
            order.amount_total = order.amount_untaxed + order.amount_tax
            order.global_discount_amount = currency.round(discount_base_total)

            # Solo setear amount_by_group si existe en este entorno
            if "amount_by_group" in order._fields:
                order.amount_by_group = self._format_amount_by_group(groups, currency)

    # Helper para formatear amount_by_group si está disponible
    def _format_amount_by_group(self, groups, currency):
        if not groups:
            return False
        sorted_groups = sorted(
            groups.values(),
            key=lambda g: g["group"].sequence if g["group"] else 0
        )
        lines = []
        for g in sorted_groups:
            name = g["group"].name if g["group"] else ""
            amount = currency.round(g["amount"])
            base = currency.round(g["base"])
            lines.append(f"{name}: {currency.symbol}{amount:,.2f} sobre {currency.symbol}{base:,.2f}")
        return "\n".join(lines)
