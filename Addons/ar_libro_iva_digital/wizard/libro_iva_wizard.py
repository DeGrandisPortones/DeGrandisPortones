from odoo import api, fields, models
from datetime import date
import base64
from math import fabs
from odoo.exceptions import UserError


class ArLibroIvaWizard(models.TransientModel):
    _name = "ar.libro.iva.wizard"
    _description = "Exportar Libro IVA Digital (AFIP / ARCA)"

    book_type = fields.Selection(
        [("sales", "Ventas"), ("purchases", "Compras")],
        required=True,
        default="purchases",
    )
    date_from = fields.Date(
        required=True,
        default=lambda s: date.today().replace(day=1),
    )
    date_to = fields.Date(
        required=True,
        default=lambda s: date.today(),
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda s: s.env.company,
    )

    # -------------------------------------------------------------------------
    # Helpers de formato
    # -------------------------------------------------------------------------

    @staticmethod
    def _num(value, length):
        """Monto con 2 decimales implícitos (x100), cero padded."""
        value = fabs(value or 0.0)
        cents = int(round(value * 100))
        s = str(cents)
        if len(s) > length:
            s = s[-length:]
        return s.rjust(length, "0")

    @staticmethod
    def _num_raw(value, length):
        """Numérico entero sin decimales, padded con ceros."""
        s = (value or "").strip()
        if not isinstance(s, str):
            s = str(s)
        s = s.replace("-", "")
        if len(s) > length:
            s = s[-length:]
        return s.rjust(length, "0")

    @staticmethod
    def _text(value, length):
        s = (value or "").upper()
        if len(s) > length:
            s = s[:length]
        return s.ljust(length, " ")

    @staticmethod
    def _ali_code_from_tax(tax):
        """Código de alícuota AFIP (4 dígitos)."""
        for field_name in ("l10n_ar_vat_afip_code", "l10n_ar_afip_code", "afip_code"):
            if hasattr(tax, field_name):
                code = getattr(tax, field_name)
                if code:
                    return str(code).rjust(4, "0")

        amount = fabs(tax.amount or 0.0)
        mapping = {
            0.0: "0003",    # Exento / 0 %
            10.5: "0004",
            21.0: "0005",
            27.0: "0006",
            5.0: "0008",
            2.5: "0009",
        }
        code = mapping.get(round(amount, 2), "0005")
        return code.rjust(4, "0")

    # -------------------------------------------------------------------------
    # Obtención de comprobantes
    # -------------------------------------------------------------------------

    def _get_moves_purchases(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", ["in_invoice", "in_refund", "in_receipt"]),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        return self.env["account.move"].search(domain, order="date, name, id")

    # -------------------------------------------------------------------------
    # Generación de TXT COMPRAS
    # -------------------------------------------------------------------------

    def _build_purchases_files(self):
        """Genera CBTE y ALICUOTAS para COMPRAS."""
        self.ensure_one()
        moves = self._get_moves_purchases()
        lines_cbte = []
        lines_ali = []

        for move in moves:
            partner = move.partner_id

            # Fecha comprobante
            fecha = (move.invoice_date or move.date or date.today()).strftime("%Y%m%d")

            # Tipo comprobante (código AFIP)
            doc_type = move.l10n_latam_document_type_id
            tipo_cbte = (
                getattr(doc_type, "l10n_ar_afip_code", False)
                or doc_type.code
                or ""
            )
            tipo_cbte = str(tipo_cbte).rjust(3, "0")

            # Punto de venta / Número de comprobante
            doc_number = move.l10n_latam_document_number or move.name or ""
            only_digits = "".join(ch for ch in doc_number if ch.isdigit())
            if len(only_digits) >= 5:
                pto_venta = only_digits[:5]
                nro_cbte = only_digits[5:]
            else:
                pto_venta = "00000"
                nro_cbte = only_digits
            pto_venta = pto_venta.rjust(5, "0")
            nro_cbte = nro_cbte.rjust(20, "0")

            # Documento vendedor
            id_type = partner.l10n_latam_identification_type_id
            cod_doc_vend = (
                getattr(id_type, "l10n_ar_afip_code", False)
                or getattr(id_type, "afip_code", False)
                or "80"
            )
            cod_doc_vend = str(cod_doc_vend).rjust(2, "0")

            nro_id = partner.vat or ""
            nro_id = "".join(ch for ch in nro_id if ch.isdigit())
            nro_id = nro_id.rjust(20, "0")

            nombre_vend = self._text(partner.name, 30)

            total = fabs(move.amount_total_signed or move.amount_total or 0.0)

            # Montos por tipo de impuesto
            imp_exento = 0.0
            imp_internos = 0.0
            imp_perc_iva = 0.0
            imp_perc_otros = 0.0
            imp_perc_iibb = 0.0
            imp_perc_muni = 0.0
            otros_tributos = 0.0

            # Bases e IVA por alícuota
            vat_bases = {}  # code -> base
            vat_taxes = {}  # code -> tax

            for line in move.line_ids:
                tax = line.tax_line_id
                if not tax:
                    continue

                group_name = (tax.tax_group_id.name or "").lower()
                amount = fabs(line.balance or line.amount_currency or 0.0)

                if "percep" in group_name and "iva" in group_name:
                    imp_perc_iva += amount
                elif "percep" in group_name and ("iibb" in group_name or "ingresos brutos" in group_name):
                    imp_perc_iibb += amount
                elif "percep" in group_name and ("munic" in group_name or "municip" in group_name):
                    imp_perc_muni += amount
                elif "interno" in group_name:
                    imp_internos += amount
                elif "iva" in group_name:
                    code = self._ali_code_from_tax(tax)
                    vat_taxes[code] = vat_taxes.get(code, 0.0) + amount
                    base = fabs(line.tax_base_amount or 0.0)
                    vat_bases[code] = vat_bases.get(code, 0.0) + base
                else:
                    otros_tributos += amount

            # Exentos: líneas sin IVA (aproximación)
            for line in move.invoice_line_ids:
                if not line.tax_ids:
                    imp_exento += fabs(line.price_subtotal or 0.0)

            # Conceptos no gravados (si no distinguís, lo dejamos en 0)
            imp_no_grav = 0.0

            # Crédito fiscal computable = suma IVA de alícuotas
            credito_fiscal = sum(vat_taxes.values())

            # Moneda y tipo de cambio
            cod_moneda = "PES"
            tipo_cambio = "0001000000"  # 1.000000
            if move.currency_id and move.currency_id != move.company_currency_id:
                try:
                    rate = fabs(move.amount_total or 0.0) / fabs(
                        move.amount_total_signed or 1.0
                    )
                except ZeroDivisionError:
                    rate = 1.0
                rate_int = int(round(rate * 10 ** 6))
                tipo_cambio = str(rate_int).rjust(10, "0")

            cant_alicuotas = max(len(vat_bases) or 1, 1)
            cod_operacion = " "  # en blanco como en los ejemplos

            # Emisor/corredor (normalmente vacío)
            cuit_emisor = "00000000000".rjust(11, "0")
            nombre_emisor = " " * 30
            iva_comision = self._num(0.0, 15)

            # -----------------------------------------------------------------
            # CABECERA COMPRAS (325 caracteres)
            # -----------------------------------------------------------------
            cbte = (
                fecha
                + tipo_cbte
                + pto_venta
                + nro_cbte
                + " " * 16  # Despacho de importación
                + cod_doc_vend
                + nro_id
                + nombre_vend
                + self._num(total, 15)
                + self._num(imp_no_grav, 15)
                + self._num(imp_exento, 15)
                + self._num(imp_perc_iva, 15)
                + self._num(imp_perc_otros, 15)
                + self._num(imp_perc_iibb, 15)
                + self._num(imp_perc_muni, 15)
                + self._num(imp_internos, 15)
                + cod_moneda
                + tipo_cambio
                + str(cant_alicuotas)[0]
                + cod_operacion
                + self._num(credito_fiscal, 15)
                + self._num(otros_tributos, 15)
                + cuit_emisor.rjust(11, "0")
                + nombre_emisor
                + iva_comision
            )
            cbte = cbte[:325].ljust(325, " ")
            lines_cbte.append(cbte)

            # -----------------------------------------------------------------
            # ALICUOTAS COMPRAS (84 caracteres)
            # -----------------------------------------------------------------
            if not vat_bases:
                code = "0003"  # Exento / sin IVA
                ali_line = (
                    tipo_cbte
                    + pto_venta
                    + nro_cbte
                    + cod_doc_vend
                    + nro_id
                    + self._num(0.0, 15)
                    + code
                    + self._num(0.0, 15)
                )
                ali_line = ali_line[:84].ljust(84, " ")
                lines_ali.append(ali_line)
            else:
                for code in sorted(vat_bases.keys()):
                    base = vat_bases.get(code, 0.0)
                    iva = vat_taxes.get(code, 0.0)
                    ali_line = (
                        tipo_cbte
                        + pto_venta
                        + nro_cbte
                        + cod_doc_vend
                        + nro_id
                        + self._num(base, 15)
                        + code
                        + self._num(iva, 15)
                    )
                    ali_line = ali_line[:84].ljust(84, " ")
                    lines_ali.append(ali_line)

        txt_cbte = "\r\n".join(lines_cbte) + ("\r\n" if lines_cbte else "")
        txt_ali = "\r\n".join(lines_ali) + ("\r\n" if lines_ali else "")
        return txt_cbte, txt_ali

    # -------------------------------------------------------------------------
    # Acción principal
    # -------------------------------------------------------------------------

    def action_export(self):
        self.ensure_one()

        if self.book_type != "purchases":
            raise UserError(
                "Por el momento este módulo sólo genera el TXT de COMPRAS "
                "para Libro IVA Digital."
            )

        txt_cbte, txt_ali = self._build_purchases_files()

        suf = "COMPRAS"
        fname1 = f"LIBRO_IVA_DIGITAL_{suf}_CBTE.txt"
        fname2 = f"LIBRO_IVA_DIGITAL_{suf}_ALICUOTAS.txt"

        a1 = self.env["ir.attachment"].create(
            {
                "name": fname1,
                "type": "binary",
                "datas": base64.b64encode(
                    txt_cbte.encode("latin1", "ignore")
                ).decode(),
                "mimetype": "text/plain",
            }
        )
        self.env["ir.attachment"].create(
            {
                "name": fname2,
                "type": "binary",
                "datas": base64.b64encode(
                    txt_ali.encode("latin1", "ignore")
                ).decode(),
                "mimetype": "text/plain",
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{a1.id}?download=1",
            "target": "self",
        }
