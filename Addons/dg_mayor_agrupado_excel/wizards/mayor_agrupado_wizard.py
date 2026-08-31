import base64
import io

import xlsxwriter

from odoo import fields, models
from odoo.exceptions import UserError


class DgMayorAgrupadoWizard(models.TransientModel):
    _name = "dg.mayor.agrupado.wizard"
    _description = "Mayor Agrupado por Factura (Excel)"

    def _default_date_from(self):
        return fields.Date.context_today(self).replace(day=1)

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )
    account_ids = fields.Many2many(
        "account.account",
        string="Cuentas",
        required=True,
        help="Cuentas a incluir en el Excel. Cada una se exporta en su propia sección, "
             "con una fila por asiento (no por línea de factura).",
    )
    date_from = fields.Date(string="Desde", required=True, default=_default_date_from)
    date_to = fields.Date(
        string="Hasta", required=True, default=lambda self: fields.Date.context_today(self)
    )

    def action_export_xlsx(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.")
        if not self.account_ids:
            raise UserError("Elegí al menos una cuenta.")

        xlsx_data = self._build_xlsx()

        attachment = self.env["ir.attachment"].create({
            "name": "Mayor Agrupado %s a %s.xlsx" % (self.date_from, self.date_to),
            "type": "binary",
            "datas": base64.b64encode(xlsx_data),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _get_account_moves(self, account):
        """Un dict por asiento (no por línea), sumando debe/haber del asiento
        para esta cuenta puntual. Usa read_group -> respeta reglas de acceso
        ORM estándar, sin tocar la maquinaria interna de account_reports."""
        AccountMoveLine = self.env["account.move.line"]
        domain = [
            ("account_id", "=", account.id),
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        groups = AccountMoveLine.read_group(
            domain, ["debit:sum", "credit:sum"], groupby=["move_id"], lazy=False
        )

        move_ids = [g["move_id"][0] for g in groups if g.get("move_id")]
        moves_by_id = {m.id: m for m in self.env["account.move"].browse(move_ids)}

        rows = []
        for g in groups:
            move_id = g["move_id"][0] if g.get("move_id") else False
            move = moves_by_id.get(move_id)
            rows.append({
                "date": move.date if move else False,
                "move_name": move.name if move else "",
                "journal": move.journal_id.name if move else "",
                "partner": move.partner_id.display_name if move and move.partner_id else "",
                "ref": (move.ref or "") if move else "",
                "debit": g.get("debit") or 0.0,
                "credit": g.get("credit") or 0.0,
            })

        rows.sort(key=lambda r: (r["date"] or fields.Date.context_today(self), r["move_name"] or ""))
        return rows

    def _build_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Mayor Agrupado")

        title_fmt = workbook.add_format({"bold": True, "font_size": 14})
        subtitle_fmt = workbook.add_format({"italic": True})
        account_fmt = workbook.add_format({"bold": True, "font_size": 12, "top": 2})
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#D9E1F2", "border": 1,
        })
        money_fmt = workbook.add_format({"num_format": "#,##0.00"})
        money_bold_fmt = workbook.add_format({"num_format": "#,##0.00", "bold": True, "top": 1})
        text_bold_fmt = workbook.add_format({"bold": True, "top": 1})

        widths = [12, 22, 14, 30, 30, 14, 14, 14]
        for col, width in enumerate(widths):
            sheet.set_column(col, col, width)

        row = 0
        sheet.write(row, 0, "Mayor Agrupado por Factura (sin arrastre)", title_fmt)
        row += 1
        sheet.write(row, 0, "Período: %s a %s" % (self.date_from, self.date_to), subtitle_fmt)
        row += 2

        headers = ["Fecha", "Asiento", "Diario", "Cliente/Proveedor", "Referencia", "Debe", "Haber", "Saldo"]

        for account in self.account_ids.sorted(key=lambda a: a.code or ""):
            sheet.write(row, 0, "%s %s" % (account.code or "", account.name or ""), account_fmt)
            row += 1

            for col, label in enumerate(headers):
                sheet.write(row, col, label, header_fmt)
            row += 1

            balance = 0.0
            total_debit = 0.0
            total_credit = 0.0
            move_rows = self._get_account_moves(account)

            if not move_rows:
                sheet.write(row, 0, "(sin movimientos en el período)")
                row += 1

            for r in move_rows:
                balance += r["debit"] - r["credit"]
                total_debit += r["debit"]
                total_credit += r["credit"]

                sheet.write(row, 0, r["date"].strftime("%d/%m/%Y") if r["date"] else "")
                sheet.write(row, 1, r["move_name"])
                sheet.write(row, 2, r["journal"])
                sheet.write(row, 3, r["partner"])
                sheet.write(row, 4, r["ref"])
                sheet.write(row, 5, r["debit"], money_fmt)
                sheet.write(row, 6, r["credit"], money_fmt)
                sheet.write(row, 7, balance, money_fmt)
                row += 1

            sheet.write(row, 4, "Totales", text_bold_fmt)
            sheet.write(row, 5, total_debit, money_bold_fmt)
            sheet.write(row, 6, total_credit, money_bold_fmt)
            sheet.write(row, 7, balance, money_bold_fmt)
            row += 3

        workbook.close()
        return output.getvalue()
