##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountCheckActionWizard(models.TransientModel):
    _name = "account.check.action.wizard"
    _description = "Account Check Action Wizard"

    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )

    def action_confirm(self):
        """Débito de cheques.

        Si el cheque LATAM está vinculado a un cheque propio DFlex, usamos la
        misma función de DFlex que crea el asiento individual:
            Debe: cuenta puente de cheques propios
            Haber: banco del diario del cheque

        Para los demás cheques se conserva el comportamiento original del
        módulo l10n_latam_check_ux.
        """
        checks = self.env["l10n_latam.check"].browse(self._context.get("active_ids", False))

        dflex_checks = checks.filtered(lambda check: "dflex_check_id" in check._fields and check.dflex_check_id)
        normal_checks = checks - dflex_checks

        for check in dflex_checks:
            dflex_check = check.dflex_check_id
            if self.date and dflex_check.payment_date and self.date < dflex_check.payment_date:
                raise UserError(
                    _("La fecha del débito del cheque %s no puede ser inferior a la fecha de pago %s.")
                    % (dflex_check.name, dflex_check.payment_date)
                )
            dflex_check.with_context(dflex_debit_date=self.date).action_debit()
            if dflex_check.debit_move_id:
                check.message_post(
                    body=(
                        f'El cheque propio DFlex nro "{dflex_check.name}" ha sido debitado. '
                        + dflex_check.debit_move_id._get_html_link()
                    )
                )
            else:
                check.message_post(body=f'El cheque propio DFlex nro "{dflex_check.name}" ha sido debitado.')

        if not normal_checks:
            return True

        if normal_checks.filtered(lambda x: not x.check_add_debit_button):
            raise UserError(_("At least one check is in a journal where the 'Add Debit Date' option is not enabled."))
        for check in normal_checks:
            if self.date < check.payment_id.date:
                raise UserError(
                    _("La fecha del débito del cheque %s no puede ser inferior a la fecha de emisión del mismo %s.")
                    % (self.date, check.payment_id.date)
                )
            move_line_id = check.outstanding_line_id.ids
            outstanding_account = self._get_outstanding_account(check)
            label = f"Débito cheque nro {check.name}"
            new_mv_line_dicts = {
                "label": label,
                "amount": abs(sum(check.outstanding_line_id.mapped("balance"))),
                "account_id": outstanding_account.id,
                "journal_id": check.original_journal_id.id,
                "move_line_ids": move_line_id,
                "date": self.date,
            }
            wizard = (
                self.env["account.reconcile.wizard"]
                .with_context(active_model="account.move.line", active_ids=move_line_id)
                .create(new_mv_line_dicts)
            )
            wizard.reconcile()
            debit_move = self.env["account.move"].search(
                [("line_ids.name", "=", label), ("date", "=", self.date)], limit=1
            )
            if debit_move:
                check.message_post(
                    body=f'El cheque nro "{check.name}" ha sido debitado. ' + debit_move._get_html_link()
                )
            else:
                check.message_post(
                    body=f'El cheque nro "{check.name}" ha sido debitado, pero no se encontró el asiento asociado.'
                )
        return True

    def _get_outstanding_account(self, check):
        """Obtenemos la cuenta para hacer el débito de cheques y hacemos las validaciones correspondientes."""
        journal = check.original_journal_id
        journal_manual_payment_method = journal.outbound_payment_method_line_ids.filtered(lambda x: x.code == "manual")
        if not journal_manual_payment_method:
            raise UserError(
                _("No es posible crear un nuevo débito de cheque sin un método de pagos 'manual' en el diario %s.")
                % (journal.display_name)
            )
        if len(journal_manual_payment_method) > 1:
            if journal_manual_payment_method.filtered(lambda x: x.name == "Manual"):
                journal_manual_payment_method = journal_manual_payment_method.filtered(lambda x: x.name == "Manual")
            journal_manual_payment_method = journal_manual_payment_method.sorted()[0]
        return journal_manual_payment_method.payment_account_id
