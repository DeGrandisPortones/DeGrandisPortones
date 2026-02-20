from odoo import Command, _, api, models
from odoo.exceptions import ValidationError


class L10nLatamPaymentMassTransfer(models.TransientModel):
    _inherit = "l10n_latam.payment.mass.transfer"

    DEPOSIT_METHOD_LINE_NAME = "Depósito Cheques Terceros"

    @api.model
    def default_get(self, fields_list):
        """Patch para Odoo 18: en el wizard estándar se hace `raise '...'` (string)
        y termina en TypeError. Convertimos ese caso en un ValidationError usable.
        """
        try:
            return super().default_get(fields_list)
        except TypeError:
            raise ValidationError(
                _(
                    "You have select some payments that are not checks. "
                    "Please call this action from the Third Party Checks menu"
                )
            )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_third_party_checks(self):
        """Trabajamos solo con cheques de terceros (new_third_party_checks) y misma moneda."""
        self.ensure_one()
        if not self.check_ids:
            return self.env["l10n_latam.check"]
        currency = self.check_ids[0].currency_id
        return self.check_ids.filtered(
            lambda c: c.payment_method_line_id.code == "new_third_party_checks" and c.currency_id == currency
        )

    def _get_checks_cartera_account(self, checks):
        """Determina la cuenta de 'cartera' (Cheques de Terceros) a acreditar en el depósito."""
        self.ensure_one()
        if not checks:
            raise ValidationError(_("No hay cheques seleccionados para depositar."))

        # 1) Preferimos la cuenta de la línea outstanding del cheque (es la más fiel al asiento real).
        outstanding_accounts = checks.mapped("outstanding_line_id.account_id")
        account = outstanding_accounts[:1]
        if not account:
            # 2) Fallback: cuenta del método de pago del payment original.
            account = checks.mapped("payment_id.payment_method_line_id.payment_account_id")[:1]

        if not account:
            raise ValidationError(
                _(
                    "No se pudo determinar la cuenta de cartera para los cheques seleccionados. "
                    "Revisá que los cheques tengan línea outstanding y/o método de pago configurado con cuenta pendiente."
                )
            )
        return account

    def _get_or_create_deposit_method_line(self, bank_journal, cartera_account):
        """Busca/crea un método de pago ENTRANTE manual en el banco con cuenta pendiente = cartera."""
        self.ensure_one()

        manual_lines = bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == "manual")

        # Si ya existe uno con la cuenta de cartera, lo reutilizamos.
        line = manual_lines.filtered(lambda l: l.payment_account_id == cartera_account)[:1]
        if line:
            return line

        # Si existe uno con el nombre esperado, lo ajustamos a la cuenta de cartera.
        line = manual_lines.filtered(lambda l: l.name == self.DEPOSIT_METHOD_LINE_NAME)[:1]
        if line:
            line.payment_account_id = cartera_account
            return line

        # Creamos uno nuevo.
        manual_method = self.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")],
            limit=1,
        )
        if not manual_method:
            raise ValidationError(
                _(
                    "No se encontró el método de pago 'manual' (inbound). "
                    "Verificá que el módulo de Contabilidad esté instalado y el diario tenga métodos de pago habilitados."
                )
            )

        return self.env["account.payment.method.line"].create(
            {
                "name": self.DEPOSIT_METHOD_LINE_NAME,
                "journal_id": bank_journal.id,
                "payment_method_id": manual_method.id,
                "payment_account_id": cartera_account.id,
            }
        )

    # -------------------------------------------------------------------------
    # Main logic
    # -------------------------------------------------------------------------

    def _create_payments(self):
        """Depósito directo: Dr Banco / Cr Cheques de Terceros (cartera)."""
        self.ensure_one()

        if self.destination_journal_id.company_id != self.journal_id.company_id:
            raise ValidationError(
                _("In order to transfer checks between branches you need to use internal transfer menu.")
            )

        checks = self._get_third_party_checks()
        if not checks:
            raise ValidationError(_("No se encontraron cheques de terceros válidos para depositar."))

        if self.split_payment:
            return self._create_split_payments()

        cartera_account = self._get_checks_cartera_account(checks)
        method_line = self._get_or_create_deposit_method_line(self.destination_journal_id, cartera_account)

        payment = (
            self.env["account.payment"]
            .with_context(check_deposit_transfer=True)
            .create(
                {
                    "date": self.payment_date,
                    "amount": sum(checks.mapped("amount")),
                    "partner_id": self.env.company.partner_id.id,
                    "payment_type": "inbound",
                    "memo": self.communication,
                    "journal_id": self.destination_journal_id.id,
                    "currency_id": checks[0].currency_id.id,
                    "payment_method_line_id": method_line.id,
                    "l10n_latam_move_check_ids": [Command.link(c.id) for c in checks],
                }
            )
        )

        # Si el método no es de cheques, Odoo AR puede intentar "remover" el cheque. Lo evitamos.
        payment.with_context(l10n_ar_skip_remove_check=True).action_post()
        return payment

    def _create_split_payments(self):
        """Un pago por cheque: Dr Banco / Cr Cheques de Terceros."""
        self.ensure_one()

        checks = self._get_third_party_checks()
        if not checks:
            raise ValidationError(_("No se encontraron cheques de terceros válidos para depositar."))

        cartera_account = self._get_checks_cartera_account(checks)
        method_line = self._get_or_create_deposit_method_line(self.destination_journal_id, cartera_account)

        payments = self.env["account.payment"]
        for check in checks:
            payment = (
                self.env["account.payment"]
                .with_context(check_deposit_transfer=True)
                .create(
                    {
                        "date": self.payment_date,
                        "amount": check.amount,
                        "partner_id": self.env.company.partner_id.id,
                        "payment_type": "inbound",
                        "memo": self.communication,
                        "journal_id": self.destination_journal_id.id,
                        "currency_id": check.currency_id.id,
                        "payment_method_line_id": method_line.id,
                        "l10n_latam_move_check_ids": [Command.link(check.id)],
                    }
                )
            )
            payment.with_context(l10n_ar_skip_remove_check=True).action_post()
            payments |= payment

        return payments
