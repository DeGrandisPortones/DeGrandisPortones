from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("use_payment_pro", "main_payment_id", "company_id", "payment_type")
    def _compute_available_journal_ids(self):
        """Keep the Multiple payments journal selectable on main payments.

        The base l10n_ar_payment_bundle logic removes the payment bundle journal
        from available_journal_ids for linked payments, which is correct because
        linked payments must be real methods such as cash, bank, third-party
        checks, etc. In this database the same filter can also hide the Multiple
        payments journal from the main customer collection form. This override
        preserves the original exclusion for linked payments and explicitly adds
        the bundle journal back for top-level payments of the matching company.
        """
        super()._compute_available_journal_ids()
        Journal = self.env["account.journal"]
        for rec in self:
            if not rec.company_id:
                continue
            bundle_journal_id = rec.company_id._get_bundle_journal(rec.payment_type)
            bundle_journal = Journal.browse(bundle_journal_id).exists()
            if not bundle_journal:
                continue

            # Do not allow a payment bundle inside another payment bundle.
            if rec.main_payment_id:
                rec.available_journal_ids = rec.available_journal_ids.filtered(
                    lambda journal: journal._origin.id != bundle_journal.id and not journal._origin.currency_id
                )
                continue

            # Main payment: make Multiple payments visible/selectable.
            available = rec.available_journal_ids.filtered(lambda journal: not journal._origin.currency_id)
            if bundle_journal not in available:
                available |= bundle_journal
            rec.available_journal_ids = available
