from odoo import _, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _dg_new_third_party_checks_for_withholding_fix(self):
        """Payments that use an existing third-party check as incoming payment.

        l10n_ar_tax already has special handling for check payments, but it only
        includes the classic codes in_third_party_checks/out_third_party_checks.
        The UX flow for incoming existing third-party checks uses the code
        new_third_party_checks, so withholdings could be posted without updating
        the paid counterpart amount.
        """
        return self.filtered(lambda payment: payment.payment_method_code == "new_third_party_checks")

    def action_confirm(self):
        """Apply the same protection used by l10n_ar_tax for check payments.

        If withholdings change the total amount to pay, block confirmation and
        ask the user to compute the check payment amount first. This avoids
        posting an entry where the withholding line is present but the customer
        receivable is only credited for the check net amount.
        """
        checks_payments = self._dg_new_third_party_checks_for_withholding_fix()
        for rec in checks_payments:
            previous_to_pay = rec.to_pay_amount
            rec.compute_withholdings()
            if not rec.currency_id.is_zero(previous_to_pay - rec.to_pay_amount):
                raise UserError(
                    _(
                        "Está pagando con un cheque y las retenciones que se aplicarán "
                        "cambiarán el importe a pagar de %s a %s.\n"
                        "Por favor, compute las retenciones para que el importe a pagar "
                        "se actualice y luego confirme el pago."
                    )
                    % (previous_to_pay, rec.to_pay_amount)
                )
        return super().action_confirm()

    def compute_to_pay_amount_for_check(self):
        """Also support new_third_party_checks in the check amount helper."""
        res = super().compute_to_pay_amount_for_check()

        checks_payments = self._dg_new_third_party_checks_for_withholding_fix()
        for rec in checks_payments.with_context(skip_account_move_synchronization=True):
            remaining_attempts = 230
            while not rec.currency_id.is_zero(rec.payment_difference):
                if remaining_attempts == 0:
                    raise UserError(
                        _(
                            "Máximo de intentos alcanzado. No pudimos computar el importe a pagar. "
                            'El último importe a pagar al que llegamos fue "%s"'
                        )
                        % rec.to_pay_amount
                    )
                remaining_attempts -= 1

                if -rec.payment_difference > 2:
                    rec.to_pay_amount -= rec.payment_difference
                elif -rec.payment_difference > 0:
                    rec.to_pay_amount += 0.01
                elif rec.to_pay_amount > rec.amount:
                    rec.to_pay_amount = 0.0
                else:
                    raise UserError(
                        _(
                            "Hubo un error al querer computar el importe a pagar. "
                            "Llegamos a estos valores:\n"
                            "* to_pay_amount: %s\n"
                            "* payment_difference: %s\n"
                            "* amount: %s"
                        )
                        % (rec.to_pay_amount, rec.payment_difference, rec.amount)
                    )

            rec.with_context(skip_account_move_synchronization=False)._synchronize_to_moves(
                {"l10n_ar_withholding_line_ids"}
            )

        return res
