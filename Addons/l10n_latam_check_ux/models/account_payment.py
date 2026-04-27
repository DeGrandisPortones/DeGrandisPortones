from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_latam_move_check_ids_operation_date = fields.Datetime(
        string="Operation Date",
        default=fields.Datetime.now(),
    )

    def _dflex_skip_l10n_latam_check_warning(self):
        """Skip native LATAM amount warning for DFlex own-check payments."""
        self.ensure_one()
        if self.env.context.get("dflex_skip_l10n_latam_check_warning"):
            return True
        for field_name in ("dflex_check_line_ids", "dflex_own_check_line_ids", "dflex_payment_check_line_ids"):
            if field_name in self._fields and self[field_name]:
                return True
        if "dflex_check_id" in self._fields and self.dflex_check_id:
            return True
        payment_method_line = self.payment_method_line_id
        if not payment_method_line:
            return False
        method_code = payment_method_line.code or payment_method_line.payment_method_id.code
        method_name = " ".join(
            part for part in [payment_method_line.name, payment_method_line.payment_method_id.name] if part
        ).lower()
        return bool(
            method_code == "own_checks"
            or "cheques propios" in method_name
            or "own check" in method_name
        )

    def action_post(self):
        # Nosotros queremos bloquear también nros. de cheques de terceros que sean únicos.
        # Excepción: cheques propios DFlex. En ese flujo no se usa l10n_latam_new_check_ids,
        # por lo que el warning nativo de monto no aplica.
        for rec in self:
            skip_warning = rec._dflex_skip_l10n_latam_check_warning()
            if skip_warning and "l10n_latam_check_warning_msg" in rec._fields:
                rec.l10n_latam_check_warning_msg = False
            if not skip_warning and rec.l10n_latam_check_warning_msg:
                raise ValidationError("%s" % rec.l10n_latam_check_warning_msg)
            rec.l10n_latam_move_check_ids_operation_date = fields.Datetime.now()
        super().action_post()

    def _create_paired_internal_transfer_payment(self):
        """
        Two modifications when only when transferring from a third party checks journal:
        1. When a paired transfer is created, the default odoo behavior is to use on the paired transfer the first
        available payment method. If we are transferring to another third party checks journal, then set as payment
        method on the paired transfer 'in_third_party_checks' or 'out_third_party_checks'
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
