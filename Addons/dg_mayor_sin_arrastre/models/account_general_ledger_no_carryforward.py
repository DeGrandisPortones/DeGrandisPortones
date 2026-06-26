import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        col_groups = options.get('column_groups') or {}
        _logger.warning("MSA_DEBUG _custom_options_initializer: column_groups keys=%s", list(col_groups.keys()))

        # Setear en el nivel raiz (va a llegar a options_group via **options en _get_column_group_options)
        options['general_ledger_strict_range'] = True

        # Intentar tambien en forced_options de cada column_group
        for key, column_group in col_groups.items():
            forced = column_group.get('forced_options')
            _logger.warning("MSA_DEBUG column_group[%s] forced_options type=%s", key, type(forced).__name__)
            try:
                forced['general_ledger_strict_range'] = True
                _logger.warning("MSA_DEBUG forced_options[%s] set OK", key)
            except Exception as e:
                _logger.warning("MSA_DEBUG forced_options[%s] ERROR: %s", key, e)

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
        _logger.warning("MSA_DEBUG _get_initial_balance_values: %d accounts", len(result))
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
