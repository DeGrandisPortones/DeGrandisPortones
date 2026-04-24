from odoo import models, tools


class ResCompany(models.Model):
    _inherit = "res.company"

    @tools.ormcache("self.id", "payment_type")
    def _get_bundle_journal(self, payment_type: str) -> int:
        method_field = (
            "inbound_payment_method_line_ids"
            if payment_type == "inbound"
            else "outbound_payment_method_line_ids"
        )
        return (
            self.env["account.journal"]
            .search(
                [
                    (f"{method_field}.payment_method_id.code", "=", "payment_bundle"),
                    ("company_id", "=", self.id),
                ],
                limit=1,
            )
            .id
        )
