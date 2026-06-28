import logging
from odoo import models

_logger = logging.getLogger(__name__)


class AccountGeneralLedgerReportHandlerNoCarryForward(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _is_sin_arrastre(self, report, options=None):
        ref = self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )
        if not ref:
            return False
        if report.id == ref.id:
            return True
        if options and options.get('sin_arrastre'):
            return True
        if options and options.get('report_id') == ref.id:
            return True
        return False

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        is_sa = self._is_sin_arrastre(report, options)
        _logger.warning(
            'SA _custom_options_initializer: report.id=%s is_sin_arrastre=%s col_groups=%s',
            report.id, is_sa, list((options.get('column_groups') or {}).keys()),
        )

        if not is_sa:
            return

        col_groups = options.get('column_groups') or {}
        if not col_groups:
            _logger.warning('SA _custom_options_initializer: col_groups VACIO, no se aplica strict_range')
            return

        options['column_groups'] = {
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
        _logger.warning('SA _custom_options_initializer: strict_range aplicado a %s col_groups', len(col_groups))

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
        is_sa = self._is_sin_arrastre(report, options)
        _logger.warning(
            'SA _get_initial_balance_values: report.id=%s is_sin_arrastre=%s cuentas=%s',
            report.id, is_sa, len(result),
        )
        if not is_sa:
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
