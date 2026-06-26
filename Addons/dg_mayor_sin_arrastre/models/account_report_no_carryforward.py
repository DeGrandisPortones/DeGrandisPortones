from odoo import models


class AccountReportNoCarryForward(models.Model):
    _inherit = 'account.report'

    def _init_options_columns(self, *args, **kwargs):
        ref = self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )
        if ref and self.id == ref.id and self.root_report_id:
            return self.root_report_id._init_options_columns(*args, **kwargs)
        return super()._init_options_columns(*args, **kwargs)
