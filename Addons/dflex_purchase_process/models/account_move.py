from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _dflex_update_purchase_process_paid_state(self):
        purchase_orders = self.env["purchase.order"]

        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue

            orders = self.env["purchase.order"]
            for line in move.invoice_line_ids:
                if "purchase_line_id" in line._fields and line.purchase_line_id:
                    orders |= line.purchase_line_id.order_id

            purchase_orders |= orders

        if purchase_orders:
            purchase_orders._dflex_update_paid_state_from_bills()

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {"payment_state", "state", "invoice_line_ids", "line_ids"}
        if trigger_fields.intersection(vals):
            self._dflex_update_purchase_process_paid_state()
        return res

    def action_post(self):
        res = super().action_post()
        self._dflex_update_purchase_process_paid_state()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._dflex_update_purchase_process_paid_state()
        return res
