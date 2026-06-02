from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @staticmethod
    def _dg_line_balance(line):
        """Return line balance from Odoo move line vals.

        Odoo 18 usually uses balance-style values here, but some flows/modules can
        still return debit/credit-style values. This helper supports both.
        """
        if "balance" in line:
            return line.get("balance") or 0.0
        return (line.get("debit") or 0.0) - (line.get("credit") or 0.0)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance=force_balance)

        self.ensure_one()
        wth_amount = sum(self.l10n_ar_withholding_line_ids.mapped("amount"))
        if not wth_amount or not self.destination_account_id:
            return res

        # The parent l10n_ar_tax method adds the withholding line, but in Odoo 18
        # the counterpart adjustment can be missed when the generated vals use
        # balance instead of debit/credit. When that happens, Odoo later creates an
        # automatic balancing line against the bank journal account.
        total_balance = sum(self._dg_line_balance(line) for line in res)
        if self.company_currency_id.is_zero(total_balance):
            return res

        destination_line = next(
            (line for line in res if line.get("account_id") == self.destination_account_id.id),
            None,
        )
        if not destination_line:
            return res

        delta_balance = -total_balance
        conversion_rate = self.exchange_rate or 1.0

        if "balance" in destination_line:
            destination_line["balance"] = (destination_line.get("balance") or 0.0) + delta_balance
        elif delta_balance < 0 and "credit" in destination_line:
            destination_line["credit"] = (destination_line.get("credit") or 0.0) - delta_balance
        elif delta_balance > 0 and "debit" in destination_line:
            destination_line["debit"] = (destination_line.get("debit") or 0.0) + delta_balance

        if not self._use_counterpart_currency() and "amount_currency" in destination_line:
            destination_line["amount_currency"] = (
                destination_line.get("amount_currency") or 0.0
            ) + (delta_balance / conversion_rate)

        return res
