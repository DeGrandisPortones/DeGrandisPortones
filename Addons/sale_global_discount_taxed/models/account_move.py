# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    global_discount_rate = fields.Float(
        string="Descuento global (%)",
        help="Porcentaje global aplicado (propagado del pedido). "
             "Si es 0 no afecta las líneas.",
        default=0.0,
        digits=(16, 4),
    )
    global_discount_amount = fields.Monetary(
        string="Descuento global (importe)",
        compute="_compute_discount_header_amounts",
        store=False,
        currency_field="currency_id",
        help="Importe total descontado sobre la base imponible (antes de impuestos).",
    )
    amount_untaxed_before_global = fields.Monetary(
        string="Subtotal (antes de descuento)",
        compute="_compute_discount_header_amounts",
        store=False,
        currency_field="currency_id",
        help="Subtotal con descuento de línea pero ANTES del descuento global aplicado a líneas.",
    )

    @api.constrains("global_discount_rate")
    def _check_global_discount_rate(self):
        for move in self:
            v = move.global_discount_rate or 0.0
            if v < 0.0 or v > 100.0:
                raise ValidationError(
                    "El Descuento global debe estar entre 0 y 100 "
                    "(o 0.0–1.0 si se guarda como fracción)."
                )

    @api.depends("invoice_line_ids.price_unit",
                 "invoice_line_ids.quantity",
                 "invoice_line_ids.discount",
                 "invoice_line_ids.tax_ids",
                 "global_discount_rate",
                 "currency_id")
    def _compute_discount_header_amounts(self):
        """
        Solo para mostrar en el encabezado de la factura:
        - Subtotal antes de global
        - Importe global descontado (derivado de descuentos de líneas)
        NOTA: En facturas ya aplicamos el % global dentro del discount de cada línea
        al crear la factura; por eso aquí solo derivamos.
        """
        for move in self:
            cur = move.currency_id
            subtotal_before = 0.0
            subtotal_after = 0.0

            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == False):
                ld = (line.discount or 0.0) / 100.0
                # Precio con descuento (ya incluye el global porque lo combinamos al crear la factura)
                price_after = line.price_unit * (1.0 - ld) * line.quantity
                subtotal_after += price_after

                # Si queremos inferir "antes del global", necesitamos el global efectivo g.
                raw = move.global_discount_rate or 0.0
                g = raw if raw <= 1.0 else (raw / 100.0)
                # 'ld' actual incluye global; para aproximar el 'antes del global':
                # asumimos que ld_total = 1 - (1 - ld_linea_original)*(1 - g)
                # si desconocemos ld_linea_original, usamos una aproximación inversa:
                approx_line = 1.0 - ((1.0 - ld) / (1.0 - g)) if g and (1.0 - g) != 0 else ld
                # precio con solo descuento de línea aproximado:
                price_before = line.price_unit * (1.0 - approx_line) * line.quantity
                subtotal_before += price_before

            move.amount_untaxed_before_global = cur.round(subtotal_before)
            move.global_discount_amount = cur.round(max(0.0, subtotal_before - subtotal_after))
