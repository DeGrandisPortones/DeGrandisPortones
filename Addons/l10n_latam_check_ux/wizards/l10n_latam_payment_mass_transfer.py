from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class L10nLatamPaymentMassTransfer(models.TransientModel):
    _inherit = "l10n_latam.payment.mass.transfer"

    DEPOSIT_METHOD_LINE_NAME = "Deposito Cheques Terceros"

    main_company_id = fields.Many2one(
        "res.company",
        compute="_compute_main_company",
    )
    destination_journal_id = fields.Many2one(
        check_company=False,
        domain="[('type', 'in', ('bank', 'cash')), ('id', '!=', journal_id), ('company_id', 'child_of', main_company_id)]",
    )
    check_ids = fields.Many2many(
        check_company=False,
    )
    split_payment = fields.Boolean(
        help="If this option is selected, each check will be registered as an individual payment instead of being grouped into a single payment."
    )

    @api.model
    def default_get(self, fields_list):
        """Odoo 18 compatibility: the standard wizard may raise a string.
        Convert that case into a real ValidationError.
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

    @api.depends("company_id")
    def _compute_main_company(self):
        for rec in self:
            rec.main_company_id = rec.company_id.parent_id or rec.company_id

    def _get_third_party_checks(self):
        """Work only with third-party checks and one currency."""
        self.ensure_one()
        if not self.check_ids:
            return self.env["l10n_latam.check"]
        currency = self.check_ids[0].currency_id
        return self.check_ids.filtered(
            lambda c: c.payment_method_line_id.code == "new_third_party_checks" and c.currency_id == currency
        )

    def _get_checks_cartera_account(self, checks):
        """Return the checks-in-wallet account to credit in the deposit."""
        self.ensure_one()
        if not checks:
            raise ValidationError(_("No hay cheques seleccionados para depositar."))

        outstanding_accounts = checks.mapped("outstanding_line_id.account_id")
        account = outstanding_accounts[:1]
        if not account:
            account = checks.mapped("payment_id.payment_method_line_id.payment_account_id")[:1]

        if not account:
            raise ValidationError(
                _(
                    "No se pudo determinar la cuenta de cartera para los cheques seleccionados. "
                    "Revisa que los cheques tengan linea outstanding y/o metodo de pago configurado con cuenta pendiente."
                )
            )
        return account

    def _get_or_create_deposit_method_line(self, bank_journal, cartera_account):
        """Find/create an inbound manual payment method line in the bank journal.

        The payment account is the third-party checks wallet account so the
        generated deposit entry is Dr Bank / Cr Third-party checks wallet.
        """
        self.ensure_one()

        manual_lines = bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == "manual")

        line = manual_lines.filtered(lambda l: l.payment_account_id == cartera_account)[:1]
        if line:
            return line

        line = manual_lines.filtered(lambda l: l.name == self.DEPOSIT_METHOD_LINE_NAME)[:1]
        if line:
            line.payment_account_id = cartera_account
            return line

        manual_method = self.env["account.payment.method"].search(
            [("code", "=", "manual"), ("payment_type", "=", "inbound")],
            limit=1,
        )
        if not manual_method:
            raise ValidationError(
                _(
                    "No se encontro el metodo de pago 'manual' (inbound). "
                    "Verifica que el modulo de Contabilidad este instalado y el diario tenga metodos de pago habilitados."
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

    def _create_payments(self):
        """Direct deposit: Dr Bank / Cr Third-party checks wallet.

        When split_payment is enabled, one payment is created for each check.
        """
        self.ensure_one()

        if self.destination_journal_id.company_id != self.journal_id.company_id:
            raise ValidationError(
                _("In order to transfer checks between branches you need to use internal transfer menu.")
            )

        checks = self._get_third_party_checks()
        if not checks:
            raise ValidationError(_("No se encontraron cheques de terceros validos para depositar."))

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

        payment.with_context(l10n_ar_skip_remove_check=True).action_post()
        return payment

    def _create_split_payments(self):
        """Create one deposit payment per check."""
        self.ensure_one()

        checks = self._get_third_party_checks()
        if not checks:
            raise ValidationError(_("No se encontraron cheques de terceros validos para depositar."))

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

    @api.constrains("check_ids")
    def _check_company_matches_active_company(self):
        for wizard in self:
            if not wizard.check_ids:
                continue
            company = wizard.check_ids.mapped("company_id")
            if len(company) > 1:
                raise ValidationError(_("All selected checks must belong to the same company."))
            if company.id != self.env.company.id:
                raise ValidationError(
                    _(
                        "Operation not allowed: To transfer the checks, you must be operating in the same company "
                        "where the checks are registered. Please switch to the appropriate company and try again."
                    )
                )
