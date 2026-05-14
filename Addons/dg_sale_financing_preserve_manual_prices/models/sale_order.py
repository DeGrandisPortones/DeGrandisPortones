# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _dg_order_line_commands_touch_pricing(self, commands):
        """Detecta si el guardado de la orden trae cambios de precio/descuento.

        En ese caso se debe respetar lo que viene desde la pantalla y evitar
        que el módulo de financiación vuelva a calcular la línea desde la
        lista de precios.
        """
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or len(command) < 3:
                continue
            values = command[2]
            if isinstance(values, dict) and ({"price_unit", "discount"} & set(values)):
                return True
        return False

    def write(self, vals):
        financing_header_fields = {
            "financing_plan_id",
            "financing_card_type",
            "financing_rate_id",
            "pricelist_id",
        }

        if "order_line" in vals and not self.env.context.get("skip_financing_recompute"):
            line_pricing_changed = self._dg_order_line_commands_touch_pricing(vals.get("order_line"))

            # Caso principal: guardar cambios sobre líneas de venta no debe
            # disparar nuevamente el recálculo de financiación, porque pisa
            # el precio/descuento manual con el precio de lista.
            #
            # Si además viene price_unit/discount en el comando de línea,
            # también se saltea aunque haya cambios de cabecera en el mismo
            # guardado: se prioriza conservar lo que el usuario dejó en pantalla.
            if line_pricing_changed or not (financing_header_fields & set(vals)):
                orders = self.with_context(skip_financing_recompute=True)
                return super(SaleOrder, orders).write(vals)

        return super().write(vals)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("product_id", "product_uom_qty", "product_uom")
    def _onchange_product_reapply_financing(self):
        for line in self:
            # Solo recalculamos desde el módulo de financiación cuando
            # realmente hay una cuota/recargo seleccionado. Sin financiación,
            # Odoo debe permitir conservar precio y descuento manual.
            if line.order_id and line.order_id.financing_rate_id:
                line.order_id._recompute_financing_prices()
