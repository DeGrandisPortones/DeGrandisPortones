from odoo import Command, _, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains("currency_id")
    def _currency_in_bundle_journal(self):
        if self.filtered(
            lambda x: x.currency_id
            and "payment_bundle"
            in (x.inbound_payment_method_line_ids + x.outbound_payment_method_line_ids).mapped("code")
        ):
            raise ValidationError(
                _("You cannot assign a currency to journals that use the payment bundle payment method.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        journals = super().create(vals_list)
        if bundle_journals := journals.filtered(
            lambda x: any(line.payment_method_id.code == "payment_bundle" for line in x.inbound_payment_method_line_ids)
            or any(line.payment_method_id.code == "payment_bundle" for line in x.outbound_payment_method_line_ids)
        ):
            for journal in bundle_journals:
                start_code = "6.0.0.00.001"
                journal.default_account_id.code = (
                    self.env["account.account"].with_company(journal.company_id)._search_new_account_code(start_code)
                )
        return journals

    def write(self, vals):
        res = super().write(vals)
        if "inbound_payment_method_line_ids" in vals or "outbound_payment_method_line_ids" in vals:
            self.env.registry.clear_cache()
        return res

    @api.model
    def _ensure_payment_bundle_journals(self):
        """Ensure the "Multiple payments" journal exists and is usable.

        Some databases may have the l10n_ar_payment_bundle module installed but
        miss the journal created by the chart-template hook, or have it archived.
        This method is intentionally callable from XML data so it runs again on
        module updates, not only on first installation.
        """
        inbound_method = self.env.ref(
            "l10n_ar_payment_bundle.account_payment_in_payment_bundle",
            raise_if_not_found=False,
        )
        outbound_method = self.env.ref(
            "l10n_ar_payment_bundle.account_payment_out_payment_bundle",
            raise_if_not_found=False,
        )
        if not inbound_method or not outbound_method:
            return True

        template_codes = ["ar_ri", "ar_ex", "ar_base"]
        companies = self.env["res.company"].search([]).filtered(
            lambda company: (
                getattr(company, "country_code", False) == "AR"
                or company.chart_template in template_codes
                or (company.parent_id and company.parent_id.chart_template in template_codes)
            )
        )

        for company in companies:
            template_code = company.chart_template or company.parent_id.chart_template
            journal = self.with_context(active_test=False).search(
                [
                    ("company_id", "=", company.id),
                    "|",
                    ("name", "ilike", "Multiple payments"),
                    "|",
                    ("inbound_payment_method_line_ids.payment_method_id", "=", inbound_method.id),
                    ("outbound_payment_method_line_ids.payment_method_id", "=", outbound_method.id),
                ],
                limit=1,
            )

            if not journal and template_code in template_codes:
                ChartTemplate = self.env["account.chart.template"].with_company(company)
                journals_to_create = ChartTemplate._get_payment_bundle_account_journal(template_code)
                if journals_to_create:
                    ChartTemplate._load_data({"account.journal": journals_to_create})
                journal = self.with_context(active_test=False).search(
                    [
                        ("company_id", "=", company.id),
                        "|",
                        ("name", "ilike", "Multiple payments"),
                        "|",
                        ("inbound_payment_method_line_ids.payment_method_id", "=", inbound_method.id),
                        ("outbound_payment_method_line_ids.payment_method_id", "=", outbound_method.id),
                    ],
                    limit=1,
                )

            if not journal:
                continue

            values = {}
            if not journal.active:
                values["active"] = True
            if journal.currency_id:
                values["currency_id"] = False
            if journal.type != "cash":
                values["type"] = "cash"
            if values:
                journal.write(values)

            if not journal.inbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == inbound_method
            ):
                journal.write(
                    {
                        "inbound_payment_method_line_ids": [
                            Command.create({"payment_method_id": inbound_method.id})
                        ],
                    }
                )
            if not journal.outbound_payment_method_line_ids.filtered(
                lambda line: line.payment_method_id == outbound_method
            ):
                journal.write(
                    {
                        "outbound_payment_method_line_ids": [
                            Command.create({"payment_method_id": outbound_method.id})
                        ],
                    }
                )

        return True
