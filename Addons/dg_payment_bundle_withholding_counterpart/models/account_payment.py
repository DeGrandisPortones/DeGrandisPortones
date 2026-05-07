# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dg_bundle_withholding_adjustment_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Payment Bundle Withholding Adjustment",
        readonly=True,
        copy=False,
        index=True,
    )

    def action_post(self):
        res = super().action_post()
        for payment in self:
            payment._dg_create_bundle_withholding_adjustment_move()
        return res

    def action_draft(self):
        for payment in self:
            payment._dg_remove_bundle_withholding_adjustment_move()
        return super().action_draft()

    def action_cancel(self):
        for payment in self:
            payment._dg_remove_bundle_withholding_adjustment_move()
        return super().action_cancel()

    def _dg_compare_amounts(self, amount_a, amount_b):
        self.ensure_one()
        currency = self.company_currency_id or self.company_id.currency_id
        return currency.compare_amounts(amount_a, amount_b)

    def _dg_is_bundle_withholding_adjustable(self):
        self.ensure_one()
        return (
            self.payment_method_code == "payment_bundle"
            and self.is_main_payment
            and self.withholdings_amount
            and self.move_id
            and self.move_id.state == "posted"
            and self.destination_account_id
            and self.destination_account_id.account_type in ("asset_receivable", "liability_payable")
        )

    def _dg_get_bundle_bridge_accounts(self):
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

        return accounts

    def _dg_get_bundle_bridge_line_to_adjust(self):
        self.ensure_one()

        bridge_accounts = self._dg_get_bundle_bridge_accounts()
        if not bridge_accounts:
            return self.env["account.move.line"]

        withholding_amount = abs(self.withholdings_amount)
        candidate_lines = self.move_id.line_ids.filtered(
            lambda line: (
                line.account_id in bridge_accounts
                and self._dg_compare_amounts(abs(line.balance), withholding_amount) >= 0
            )
        )

        if self.payment_type == "inbound":
            candidate_lines = candidate_lines.filtered(lambda line: line.credit > 0.0)
        elif self.payment_type == "outbound":
            candidate_lines = candidate_lines.filtered(lambda line: line.debit > 0.0)
        else:
            return self.env["account.move.line"]

        return candidate_lines[:1]

    def _dg_destination_line_already_exists(self):
        self.ensure_one()

        withholding_amount = abs(self.withholdings_amount)
        destination_lines = self.move_id.line_ids.filtered(
            lambda line: (
                line.account_id == self.destination_account_id
                and line.partner_id == self.partner_id
            )
        )

        if self.payment_type == "inbound":
            return any(
                self._dg_compare_amounts(line.credit, withholding_amount) >= 0
                for line in destination_lines
            )

        if self.payment_type == "outbound":
            return any(
                self._dg_compare_amounts(line.debit, withholding_amount) >= 0
                for line in destination_lines
            )

        return False

    def _dg_prepare_bundle_withholding_adjustment_move_vals(self, bridge_account):
        self.ensure_one()

        amount = abs(self.withholdings_amount)
        name = _("Reclasificación retenciones - %s") % (self.name or self.ref or self.id)

        bridge_line_vals = {
            "name": name,
            "account_id": bridge_account.id,
            "partner_id": self.partner_id.id,
        }
        destination_line_vals = {
            "name": name,
            "account_id": self.destination_account_id.id,
            "partner_id": self.partner_id.id,
        }

        if self.payment_type == "inbound":
            bridge_line_vals.update({
                "debit": amount,
                "credit": 0.0,
            })
            destination_line_vals.update({
                "debit": 0.0,
                "credit": amount,
            })
        else:
            bridge_line_vals.update({
                "debit": 0.0,
                "credit": amount,
            })
            destination_line_vals.update({
                "debit": amount,
                "credit": 0.0,
            })

        return {
            "move_type": "entry",
            "date": self.date or fields.Date.context_today(self),
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "ref": name,
            "dg_bundle_withholding_payment_id": self.id,
            "line_ids": [
                (0, 0, bridge_line_vals),
                (0, 0, destination_line_vals),
            ],
        }

    def _dg_create_bundle_withholding_adjustment_move(self):
        self.ensure_one()

        if not self._dg_is_bundle_withholding_adjustable():
            return False

        if self.dg_bundle_withholding_adjustment_move_id:
            return self.dg_bundle_withholding_adjustment_move_id

        existing_move = self.env["account.move"].search(
            [
                ("dg_bundle_withholding_payment_id", "=", self.id),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if existing_move:
            self.dg_bundle_withholding_adjustment_move_id = existing_move.id
            return existing_move

        if self._dg_destination_line_already_exists():
            return False

        bridge_line = self._dg_get_bundle_bridge_line_to_adjust()
        if not bridge_line:
            return False

        move_vals = self._dg_prepare_bundle_withholding_adjustment_move_vals(bridge_line.account_id)
        adjustment_move = self.env["account.move"].create(move_vals)
        adjustment_move.action_post()
        self.dg_bundle_withholding_adjustment_move_id = adjustment_move.id

        self._dg_reconcile_bundle_withholding_adjustment_move(adjustment_move)

        return adjustment_move

    def _dg_reconcile_bundle_withholding_adjustment_move(self, adjustment_move):
        self.ensure_one()

        destination_line = adjustment_move.line_ids.filtered(
            lambda line: (
                line.account_id == self.destination_account_id
                and line.partner_id == self.partner_id
                and not line.reconciled
            )
        )[:1]

        if not destination_line:
            return False

        invoice_lines = self.to_pay_move_line_ids.filtered(
            lambda line: (
                line.account_id == self.destination_account_id
                and line.partner_id == self.partner_id
                and not line.reconciled
            )
        )

        if not invoice_lines:
            return False

        (invoice_lines + destination_line).reconcile()
        return True

    def _dg_remove_bundle_withholding_adjustment_move(self):
        self.ensure_one()

        move = self.dg_bundle_withholding_adjustment_move_id
        if not move:
            move = self.env["account.move"].search(
                [
                    ("dg_bundle_withholding_payment_id", "=", self.id),
                    ("state", "!=", "cancel"),
                ],
                limit=1,
            )

        if not move:
            return False

        move.line_ids.remove_move_reconcile()

        if move.state == "posted":
            move.button_draft()

        move.unlink()
        self.dg_bundle_withholding_adjustment_move_id = False
        return True
