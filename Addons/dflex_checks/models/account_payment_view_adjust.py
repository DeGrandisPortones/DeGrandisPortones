from lxml import etree

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form" or not res.get("arch"):
            return res

        try:
            arch = etree.fromstring(res["arch"])
        except Exception:
            return res

        changed = False
        if arch.xpath("//field[@name='l10n_latam_new_check_ids']"):
            for field_name in ("x_studio_tipo_cheque", "ux_order_type"):
                for node in arch.xpath(
                    "//field[@name='l10n_latam_new_check_ids']//field[@name='%s']" % field_name
                ):
                    node.set("column_invisible", "parent.payment_method_code == 'own_checks'")
                    node.set("invisible", "parent.payment_method_code == 'own_checks'")
                    node.set("required", "parent.payment_method_code != 'own_checks'")
                    changed = True

        if changed:
            res["arch"] = etree.tostring(arch, encoding="unicode")
        return res
