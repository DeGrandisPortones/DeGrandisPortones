
from odoo import api, fields, models
from datetime import date
import base64

class ArLibroIvaWizard(models.TransientModel):
    _name = "ar.libro.iva.wizard"
    _description = "Exportar Libro IVA Digital (AFIP)"

    book_type = fields.Selection([("sales","Ventas"),("purchases","Compras")], required=True, default="purchases")
    date_from = fields.Date(required=True, default=lambda s: date.today().replace(day=1))
    date_to   = fields.Date(required=True, default=lambda s: date.today())
    company_id = fields.Many2one("res.company", required=True, default=lambda s: s.env.company)

    def _fmt(self, n):
        return ("%.2f" % (n or 0.0)).replace(",", ".")

    def _domain(self):
        self.ensure_one()
        types = ("out_invoice","out_refund") if self.book_type=="sales" else ("in_invoice","in_refund")
        return [
            ("company_id","=", self.company_id.id),
            ("state","=","posted"),
            ("move_type","in", types),
            ("invoice_date",">=", self.date_from),
            ("invoice_date","<=", self.date_to),
        ]

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

        txt_cbte = ("\r\n".join(cbte_lines)) + ("\r\n" if cbte_lines else "")
        txt_ali  = ("\r\n".join(ali_lines))  + ("\r\n" if ali_lines else "")
        return txt_cbte, txt_ali

    def action_export(self):
        self.ensure_one()
        moves = self.env["account.move"].search(self._domain(), order="invoice_date, name")
        txt_cbte, txt_ali = self._build_txt(moves)
        suf = "VENTAS" if self.book_type=="sales" else "COMPRAS"
        fname1 = f"LIBRO_IVA_DIGITAL_{suf}_CBTE.txt"
        fname2 = f"LIBRO_IVA_DIGITAL_{suf}_ALICUOTAS.txt"

        a1 = self.env["ir.attachment"].create({
            "name": fname1, "type":"binary",
            "datas": base64.b64encode(txt_cbte.encode("latin1","ignore")).decode(),
            "mimetype": "text/plain",
        })
        a2 = self.env["ir.attachment"].create({
            "name": fname2, "type":"binary",
            "datas": base64.b64encode(txt_ali.encode("latin1","ignore")).decode(),
            "mimetype": "text/plain",
        })
        return {"type":"ir.actions.act_url","url":f"/web/content/{a1.id}?download=1","target":"self"}
