from odoo import models


class AccountGeneralLedgerReportHandlerNoCarryForward(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        col_groups = options.get('column_groups') or {}
        if not col_groups:
            return
        new_groups = {
            key: {
                **dict(cg),
                'forced_options': {
                    **dict(cg.get('forced_options') or {}),
                    'general_ledger_strict_range': True,
                },
                'forced_domain': list(cg.get('forced_domain') or []),
            }
            for key, cg in col_groups.items()
        }
        try:
            options['column_groups'] = new_groups
        except TypeError:
            pass

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
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
