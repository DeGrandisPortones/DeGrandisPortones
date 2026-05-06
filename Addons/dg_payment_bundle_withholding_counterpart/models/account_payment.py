# -*- coding: utf-8 -*-
from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _dg_is_same_amount(self, amount_a, amount_b):
        self.ensure_one()
        currency = self.company_currency_id or self.company_id.currency_id
        return currency.compare_amounts(abs(amount_a), abs(amount_b)) == 0

    def _dg_get_bundle_bridge_account_ids(self):
        """Accounts that must not receive the withholding counterpart on a bundle.

        The original payment bundle flow uses a bridge/outstanding account for the
        main payment. That is correct for the payment method itself, but not for the
        withholding counterpart: the withholding must reduce the partner receivable
        or payable line so it can be reconciled against the invoice/bill.
        """
        self.ensure_one()
        accounts = self.env["account.account"]

        payment_method_line = self.payment_method_line_id
        if payment_method_line.payment_account_id:
            accounts |= payment_method_line.payment_account_id

        journal = self.journal_id
        if journal.default_account_id:
            accounts |= journal.default_account_id
        if getattr(journal, "suspense_account_id", False):
            accounts |= journal.suspense_account_id

        return accounts.ids

    def _dg_should_replace_bundle_line(self, line_vals, bridge_account_ids, withholding_amount):
        self.ensure_one()

        if line_vals.get("account_id") not in bridge_account_ids:
            return False

        debit = line_vals.get("debit", 0.0) or 0.0
        credit = line_vals.get("credit", 0.0) or 0.0
        balance = debit - credit

        if not self._dg_is_same_amount(balance, withholding_amount):
            return False

        if self.payment_type == "inbound":
            # Customer receipt: withholding debits the withholding asset account
            # and must credit the customer's receivable account.
            return credit > 0.0

        if self.payment_type == "outbound":
            # Supplier payment: withholding credits the withholding liability account
            # and must debit the supplier's payable account.
            return debit > 0.0

        return False

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )

        self.ensure_one()

        if (
            self.payment_method_code != "payment_bundle"
            or not self.is_main_payment
            or not self.withholdings_amount
            or not self.destination_account_id
        ):
            return res

        if self.destination_account_id.account_type not in ("asset_receivable", "liability_payable"):
            return res

        bridge_account_ids = self._dg_get_bundle_bridge_account_ids()
        if not bridge_account_ids:
            return res

        withholding_amount = self.withholdings_amount

        for line_vals in res:
            if self._dg_should_replace_bundle_line(line_vals, bridge_account_ids, withholding_amount):
                line_vals["account_id"] = self.destination_account_id.id
                line_vals["partner_id"] = self.partner_id.id
                line_vals["name"] = line_vals.get("name") or "Contrapartida retenciones"
                break

        return res
