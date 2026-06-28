from odoo import models


class AccountGeneralLedgerReportHandlerNoCarryForward(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _is_sin_arrastre(self, report):
        ref = self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )
        return bool(ref and report.id == ref.id)

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
        if not self._is_sin_arrastre(report):
            return result
        return {
            account_id: (account, {
                col_key: {
                    k: (0.0 if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                    for k, v in (vals or {}).items()
                }
                for col_key, vals in col_data.items()
            })
            for account_id, (account, col_data) in result.items()
        }
