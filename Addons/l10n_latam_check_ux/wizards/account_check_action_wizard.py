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
        """Débito/depósito de cheques.

        - Cheques propios DFlex: delega en dflex.check.action_debit().
        - Cheques de terceros/normales: crea asiento directo Dr Banco / Cr cuenta pendiente,
          porque el uso de account.reconcile.wizard estaba generando el asiento al revés.
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

            debit_move = self._create_third_party_check_debit_move(check)
            if debit_move:
                check.message_post(
                    body=f'El cheque nro "{check.name}" ha sido debitado/depositado. ' + debit_move._get_html_link()
                )
            else:
                check.message_post(
                    body=f'El cheque nro "{check.name}" ha sido debitado/depositado, pero no se encontró el asiento asociado.'
                )
        return True

    def _create_third_party_check_debit_move(self, check):
        """Crea el asiento correcto para el depósito/débito del cheque de terceros.

        Correcto:
            Debe: Banco del diario original
            Haber: Cuenta pendiente/cartera del cheque

        El flujo anterior usaba account.reconcile.wizard y podía generar:
            Debe: cuenta pendiente
            Haber: Banco
        que disminuye el banco al depositar el cheque.
        """
        outstanding_account = self._get_outstanding_account(check)
        bank_account = self._get_bank_account(check)

        outstanding_lines = check.outstanding_line_id
        amount = abs(sum(outstanding_lines.mapped("balance"))) or abs(getattr(check, "amount", 0.0) or 0.0)
        if not amount:
            raise UserError(_("No se pudo determinar el importe del cheque %s.") % check.display_name)

        label = f"Débito cheque nro {check.name}"
        partner = check.payment_id.partner_id or self.env.company.partner_id

        debit_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": check.original_journal_id.id,
                "date": self.date,
                "ref": label,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": label,
                            "account_id": bank_account.id,
                            "partner_id": partner.id or False,
                            "debit": amount,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": label,
                            "account_id": outstanding_account.id,
                            "partner_id": partner.id or False,
                            "debit": 0.0,
                            "credit": amount,
                        },
                    ),
                ],
            }
        )
        debit_move.action_post()

        # Si la cuenta pendiente es conciliable, conciliamos la línea original del cheque
        # contra el crédito nuevo de cuenta pendiente.
        try:
            original_lines = outstanding_lines.filtered(
                lambda line: line.account_id == outstanding_account and not line.reconciled
            )
            new_outstanding_lines = debit_move.line_ids.filtered(
                lambda line: line.account_id == outstanding_account and line.credit > 0 and not line.reconciled
            )
            lines_to_reconcile = original_lines | new_outstanding_lines
            if lines_to_reconcile and outstanding_account.reconcile:
                lines_to_reconcile.reconcile()
        except Exception:
            # El asiento correcto ya quedó creado. Si por configuración la conciliación
            # automática no es posible, no bloqueamos el depósito.
            pass

        return debit_move

    def _get_bank_account(self, check):
        journal = check.original_journal_id
        if not journal:
            raise UserError(_("El cheque %s no tiene diario original configurado.") % check.display_name)
        if not journal.default_account_id:
            raise UserError(_("El diario %s no tiene cuenta bancaria/default configurada.") % journal.display_name)
        return journal.default_account_id

    def _get_outstanding_account(self, check):
        """Obtenemos la cuenta pendiente/cartera que se debe acreditar al depositar el cheque."""
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

        account = journal_manual_payment_method.payment_account_id
        if not account:
            raise UserError(
                _("El método de pago manual del diario %s no tiene cuenta pendiente configurada.")
                % journal.display_name
            )
        return account
