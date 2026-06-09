from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    invoice_date = fields.Date(string="Fecha de facturación", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        # Last posted customer invoice/refund date linked to the sale order line.
        # This lets the Sales Analysis pivot be filtered/grouped by invoice date
        # instead of the sales order confirmation date.
        res["invoice_date"] = "MAX(account_move.invoice_date)"
        return res

    def _from_sale(self):
        res = super()._from_sale()
        res += """
            LEFT JOIN sale_order_line_invoice_rel sale_line_invoice_rel
                ON sale_line_invoice_rel.order_line_id = l.id
            LEFT JOIN account_move_line account_move_line_invoice
                ON account_move_line_invoice.id = sale_line_invoice_rel.invoice_line_id
            LEFT JOIN account_move account_move
                ON account_move.id = account_move_line_invoice.move_id
                AND account_move.state = 'posted'
                AND account_move.move_type IN ('out_invoice', 'out_refund')
        """
        return res
