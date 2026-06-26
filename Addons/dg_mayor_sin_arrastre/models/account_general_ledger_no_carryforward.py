from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _get_query_sums(self, report, options):
        root = report.root_report_id or report
        new_options = dict(options)
        new_options['general_ledger_strict_range'] = True
        new_col_groups = {}
        for key, cg in (options.get('column_groups') or {}).items():
            new_cg = dict(cg)
            new_cg['forced_options'] = {
                **dict(cg.get('forced_options') or {}),
                'general_ledger_strict_range': True,
            }
            new_col_groups[key] = new_cg
        new_options['column_groups'] = new_col_groups
        return super()._get_query_sums(root, new_options)

    def _get_initial_balance_values(self, report, account_ids, options):
        root = report.root_report_id or report
        result = super()._get_initial_balance_values(root, account_ids, options)
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
