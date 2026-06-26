from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        col_groups = options.get('column_groups') or {}
        debug_parts = [f'n_grupos={len(col_groups)}']

        new_groups = {}
        for key, cg in col_groups.items():
            fo = cg.get('forced_options') or {}
            debug_parts.append(f'{key}:fo_type={type(fo).__name__}')
            new_fo = dict(fo)
            new_fo['general_ledger_strict_range'] = True
            new_cg = dict(cg)
            new_cg['forced_options'] = new_fo
            new_cg['forced_domain'] = list(cg.get('forced_domain') or [])
            new_groups[key] = new_cg

        if new_groups:
            options['column_groups'] = new_groups
            debug_parts.append('groups_replaced_ok')
        else:
            debug_parts.append('groups_VACIO')

        try:
            self.env['ir.config_parameter'].sudo().set_param(
                'msa_debug_v200', '|'.join(debug_parts)
            )
        except Exception as e:
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
