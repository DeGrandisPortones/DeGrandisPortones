from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_latam_move_check_ids_operation_date = fields.Datetime(
        string="Operation Date",
        default=fields.Datetime.now(),
    )

    def _dflex_uses_own_check_lines(self):
        """Return True when DFlex own-check lines are being used for this payment.

        The native LATAM own-check warning validates l10n_latam_new_check_ids.
        DFlex own checks use their own lines/model, so that warning must not
        block posting when the payment is actually paid with DFlex own checks.
        """
        self.ensure_one()
        if self.payment_method_line_id.code != "own_checks":
            return False

        line_fields = (
            "dflex_own_check_line_ids",
            "dflex_check_line_ids",
            "dflex_payment_check_line_ids",
        )
        for field_name in line_fields:
            if field_name in self._fields and self[field_name]:
                return True

        return bool("dflex_check_id" in self._fields and self.dflex_check_id)

    def action_post(self):
        # Nosotros queremos bloquear también nros. de cheques de terceros que sean únicos.
        # Para esto chequeamos el campo computado de warnings que ya lo tiene incorporado.
        # Excepción: pagos con cheques propios DFlex. En ese flujo no se usa
        # l10n_latam_new_check_ids, por lo que el warning nativo de monto de cheque
        # no aplica y no debe bloquear la confirmación.
        for rec in self:
            if rec.l10n_latam_check_warning_msg and not rec._dflex_uses_own_check_lines():
                raise ValidationError("%s" % rec.l10n_latam_check_warning_msg)
            rec.l10n_latam_move_check_ids_operation_date = fields.Datetime.now()
        super().action_post()

    def _create_paired_internal_transfer_payment(self):
        """
        Two modifications when only when transferring from a third party checks journal:
        1. When a paired transfer is created, the default odoo behavior is to use on the paired transfer the first
        available payment method. If we are transferring to another third party checks journal, then set as
        payment method on the paired transfer 'in_third_party_checks' or 'out_third_party_checks'
        2. On the paired transfer set the l10n_latam_check_id field, this field is needed for the
        l10n_latam_check_operation_ids and also for some warnings and constrains.
        """
        # We evalute if the transfer is creating from de wizard transfer check button with check_deposit_transfer context,
        # in order to not duplicate the transfer when creating the deposit of the check from the wizard.
        # Who already create both payments at once in the _create_payments method.)
        if not self.env.context.get("check_deposit_transfer"):
            third_party_checks = self.filtered(
                lambda x: x.payment_method_line_id.code
                in ["in_third_party_checks", "out_third_party_checks", "return_third_party_checks"]
            )
            for rec in third_party_checks:
                dest_payment_method_code = (
                    "in_third_party_checks" if rec.payment_type == "outbound" else "out_third_party_checks"
                )
                dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                    lambda x: x.code == dest_payment_method_code
                )
                if dest_payment_method:
                    super(
                        AccountPayment,
                        rec.with_context(
                            default_payment_method_line_id=dest_payment_method.id,
                            default_l10n_latam_move_check_ids=rec.l10n_latam_move_check_ids,
                        ),
                    )._create_paired_internal_transfer_payment()
                else:
                    super(
                        AccountPayment,
                        rec.with_context(
                            default_l10n_latam_move_check_ids=rec.l10n_latam_move_check_ids,
                        ),
                    )._create_paired_internal_transfer_payment()

                rec.write(
                    {
                        "l10n_latam_move_check_ids_operation_date": rec.l10n_latam_move_check_ids_operation_date
                        - timedelta(seconds=1)
                    }
                )
                rec._get_latam_checks()._compute_current_journal()
                rec._get_latam_checks()._compute_company_id()

                # If the journal belongs to the third-party checks journal, posting the move was incorrectly removing the checks,
                # even though the payment method line is for checks.
                # To fix this, we replicate the same behavior as in Odoo's "transfer check" wizard by setting the proper payment method.
                correct_dest_payment_method = rec.destination_journal_id.inbound_payment_method_line_ids.filtered(
                    lambda x: x.code == "in_third_party_checks"
                )
                if correct_dest_payment_method:
                    rec.paired_internal_transfer_payment_id.payment_method_line_id = correct_dest_payment_method
            super(AccountPayment, self - third_party_checks)._create_paired_internal_transfer_payment()

    def action_draft(self):
        for rec in self:
            for check in rec.mapped("l10n_latam_move_check_ids") + rec.mapped("l10n_latam_new_check_ids"):
                last_operation = check._get_last_operation()
                if rec != last_operation:
                    raise ValidationError(
                        "You cannot reset this operation to draft because it is not the last operation for the checks."
                    )

        super().action_draft()
