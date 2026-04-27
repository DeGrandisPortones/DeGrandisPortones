from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _dflex_is_own_checks_payment(self):
        self.ensure_one()
        payment_method_line = self.payment_method_line_id
        return bool(payment_method_line and payment_method_line.code == "own_checks")

    def _compute_l10n_latam_check_warning_msg(self):
        """Keep native LATAM warnings, except for DFlex own-check payments.

        DFlex own checks are loaded through the DFlex own-check lines, while the
        native LATAM warning validates l10n_latam_new_check_ids. For own-check
        payments this produces a false error:
        "El monto del pago no coincide con el monto del cheque seleccionado".

        Clearing the warning here prevents both the visible warning and the
        action_post validation in l10n_latam_check_ux from blocking the payment.
        """
        super_method = getattr(super(AccountPayment, self), "_compute_l10n_latam_check_warning_msg", None)
        if super_method:
            super_method()

        for payment in self:
            if payment._dflex_is_own_checks_payment():
                payment.l10n_latam_check_warning_msg = False
