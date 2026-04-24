from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("use_payment_pro", "main_payment_id", "company_id", "payment_type")
    def _compute_available_journal_ids(self):
        """Keep Multiple Payments available on the main payment, but not on linked payments.

        The original payment-bundle module removes the bundle journal in some flows when
        use_payment_pro is false. That makes the existing Multiple Payments journal disappear
        from customer/supplier receipts in some databases. For child payments, the journal must
        still be hidden to avoid nesting a payment bundle inside another payment bundle.
        """
        super()._compute_available_journal_ids()
        Journal = self.env["account.journal"]
        for rec in self:
            if not rec.company_id:
                continue

            bundle_journal = Journal.browse(rec.company_id._get_bundle_journal(rec.payment_type)).exists()

            if rec.main_payment_id:
                if bundle_journal:
                    rec.available_journal_ids = rec.available_journal_ids.filtered(
                        lambda journal: journal._origin.id != bundle_journal.id and not journal._origin.currency_id
                    )
                else:
                    rec.available_journal_ids = rec.available_journal_ids.filtered(lambda journal: not journal._origin.currency_id)
                continue

            if bundle_journal and not bundle_journal.currency_id and bundle_journal.type in ("bank", "cash"):
                rec.available_journal_ids |= bundle_journal
