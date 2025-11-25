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

    # Archivos generados
    file_cbte = fields.Binary(string="Archivo comprobantes", readonly=True)
    file_cbte_name = fields.Char(string="Nombre archivo comprobantes", readonly=True)
    file_ali = fields.Binary(string="Archivo alícuotas", readonly=True)
    file_ali_name = fields.Char(string="Nombre archivo alícuotas", readonly=True)

    state = fields.Selection(
        [
            ("choose", "choose"),
            ("download", "download"),
        ],
        default="choose",
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
        s = (value or "").strip() if isinstance(value, str) else str(value or "")
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

    def _build_txt(self, moves):
        cbte_lines, ali_lines = [], []
        for mv in moves:
            fecha = mv.invoice_date and mv.invoice_date.strftime("%Y%m%d") or ""
            pv = getattr(mv, "l10n_ar_afip_pos_number", 0) or 0
            dt = getattr(mv, "l10n_ar_afip_document_type", False)
            tipo = getattr(dt, "code", "") or ""
            nro = getattr(mv, "l10n_ar_afip_document_number", "") or (mv.name or "")
            partner = mv.partner_id
            doc_code = "80" if (partner.vat and len(partner.vat.replace('-','').strip())==11) else "85"
            doc_nro = (partner.vat or "").replace("-", "").replace(" ", "")

            by_rate = {}
            for line in mv.invoice_line_ids:
                taxes = line.tax_ids.compute_all(
                    line.price_unit, quantity=line.quantity,
                    currency=mv.currency_id, product=line.product_id, partner=mv.partner_id
                )
                base = line.price_subtotal
                tl = taxes.get("taxes", [])
                share = base / (len(tl) or 1)
                for t in tl:
                    rate = round(t.get("rate", 0.0) or 0.0, 2)
                    rec = by_rate.setdefault(rate, {"neto":0.0,"iva":0.0})
                    rec["iva"] += t.get("amount", 0.0)
                    rec["neto"] += share

            neto_total = sum(v["neto"] for v in by_rate.values())
            iva_total  = sum(v["iva"]  for v in by_rate.values())
            total      = mv.amount_total

            cbte_lines.append(";".join([
                str(fecha), str(tipo), str(pv), str(nro),
                str(doc_code), str(doc_nro),
                self._fmt(total), self._fmt(neto_total), self._fmt(iva_total)
            ]))

            for rate, vals in by_rate.items():
                ali_lines.append(";".join([
                    str(tipo), str(pv), str(nro),
                    self._fmt(rate), self._fmt(vals["neto"]), self._fmt(vals["iva"])
                ]))

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

        # Nombres de archivo tipo:
        #   LID Compras 11-2025.txt
        #   LID Compras Alicuotas 11-2025.txt
        periodo = (self.date_to or self.date_from).strftime("%m-%Y")
        fname1 = f"LID Compras {periodo}.txt"
        fname2 = f"LID Compras Alicuotas {periodo}.txt"

        self.write(
            {
                "file_cbte": base64.b64encode(
                    txt_cbte.encode("latin1", "ignore")
                ),
                "file_cbte_name": fname1,
                "file_ali": base64.b64encode(
                    txt_ali.encode("latin1", "ignore")
                ),
                "file_ali_name": fname2,
                "state": "download",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "ar.libro.iva.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
