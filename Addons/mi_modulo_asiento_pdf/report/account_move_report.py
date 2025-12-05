from odoo import api, models


class ReportAccountMovePdf(models.AbstractModel):
    _name = "report.mi_modulo_asiento_pdf.report_account_move_pdf"
    _description = "Comprobante de asiento contable"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["account.move"].browse(docids)
        return {
            "doc_ids": docs.ids,
            "doc_model": "account.move",
            "docs": docs,
            "data": data or {},
        }
