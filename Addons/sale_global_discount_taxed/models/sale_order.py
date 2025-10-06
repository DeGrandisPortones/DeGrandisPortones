# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    global_discount_rate = fields.Float(
        string="Descuento global (%)",
        help="Porcentaje aplicado a todas las líneas antes del cálculo de impuestos. "
             "Con widget porcentaje puede guardarse como fracción (0..1).",
        default=0.0,
        digits=(16, 4),
    )
    global_discount_amount = fields.Monetary(
        string="Descuento global (importe)",
        compute="_amount_all",
        store=True,
        currency_field="currency_id",
        help="Importe descontado sobre la base imponible (antes de impuestos).",
    )
    amount_untaxed_before_global = fields.Monetary(
        string="Subtotal (antes de descuento)",
        compute="_amount_all",
        store=True,
        currency_field="currency_id",
        help="Subtotal con descuento por línea pero ANTES del descuento global.",
    )

    @api.constrains("global_discount_rate")
    def _check_global_discount_rate(self):
        for order in self:
            v = order.global_discount_rate or 0.0
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
        Aplica descuento global adicional por línea ANTES de impuestos (multiplicativo con el de línea).
        Recalcula amount_untaxed, amount_tax y amount_total con base ya descontada.
        """
        for order in self:
            currency = order.currency_id
            partner = order.partner_shipping_id or order.partner_id
            company = order.company_id

            amount_untaxed = 0.0
            amount_tax = 0.0
            discount_base_total = 0.0
            subtotal_before_global = 0.0
            groups = defaultdict(lambda: {'base': 0.0, 'amount': 0.0, 'group': False})

            raw = order.global_discount_rate or 0.0
            global_rate = raw if raw <= 1.0 else (raw / 100.0)

            for line in order.order_line.filtered(lambda l: not l.display_type):
                line_rate = (line.discount or 0.0) / 100.0
                effective_factor = (1.0 - line_rate) * (1.0 - global_rate)
                eff_price_unit = line.price_unit * effective_factor

                # Subtotal sin global (con descuento por línea)
                base_line_line_discount = line.price_unit * (1.0 - line_rate) * line.product_uom_qty
                subtotal_before_global += base_line_line_discount

                # Subtotal con ambos descuentos
                base_line_both_discounts = eff_price_unit * line.product_uom_qty

                # Importe global descontado en esta línea
                discount_base_total += max(0.0, base_line_line_discount - base_line_both_discounts)

                taxes_res = line.tax_id.with_context(force_company=company.id).compute_all(
                    eff_price_unit,
                    currency=currency,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=partner,
                )

                amount_untaxed += taxes_res["total_excluded"]
                amount_tax += taxes_res["total_included"] - taxes_res["total_excluded"]

                for t in taxes_res.get("taxes", []):
                    tax_obj = self.env["account.tax"].browse(t["id"])
                    group = tax_obj.tax_group_id
                    groups[group]["group"] = group
                    groups[group]["amount"] += t["amount"]
                    groups[group]["base"] += t["base"]

            order.amount_untaxed_before_global = currency.round(subtotal_before_global)
            order.global_discount_amount = currency.round(discount_base_total)
            order.amount_untaxed = currency.round(amount_untaxed)
            order.amount_tax = currency.round(amount_tax)
            order.amount_total = order.amount_untaxed + order.amount_tax

            # Solo si existe en tu edición
            if "amount_by_group" in order._fields:
                order.amount_by_group = self._format_amount_by_group(groups, currency)

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

    # --- Propagar el % a factura y aplicar descuento por línea ---
    def _create_invoices(self, grouped=False, final=False):
        moves = super()._create_invoices(grouped=grouped, final=final)
        for move in moves:
            # Copiar el % global al encabezado de la factura
            move.global_discount_rate = self.global_discount_rate

            # Normalizar % global
            raw = move.global_discount_rate or 0.0
            g = raw if raw <= 1.0 else (raw / 100.0)

            if g <= 0:
                continue

            # Aplicar descuento combinado a cada línea de producto
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == False):
                # En facturas, 'discount' es 0..100
                ld = (line.discount or 0.0) / 100.0
                combined = 1.0 - ((1.0 - ld) * (1.0 - g))
                line.discount = round(combined * 100.0, 4)

            # Recalcular totales/impuestos de la factura
            move._recompute_dynamic_lines(recompute_all_taxes=True)
            move._compute_amount()

        return moves
