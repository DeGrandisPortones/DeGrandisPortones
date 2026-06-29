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

        # Detectar modo sin_arrastre desde options (ya procesadas) O desde previous_options
        # (cuando get_options es re-invocado internamente con gl_options que ya trae el flag).
        is_sa = self._is_sin_arrastre(report, options) or \
                bool((previous_options or {}).get('sin_arrastre'))

        if not is_sa:
            return

        # Persistir el flag para que _dynamic_lines_generator y _get_initial_balance_values
        # lo detecten aunque report sea gl_root (id != ref.id).
        options['sin_arrastre'] = True

        col_groups = options.get('column_groups') or {}
        if not col_groups:
            _logger.warning('SA _custom_options_initializer: col_groups VACIO para report.id=%s', report.id)
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
        _logger.warning('SA _custom_options_initializer: strict_range OK para report.id=%s', report.id)

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        _logger.warning(
            'SA _dynamic_lines_generator LLAMADO: report.id=%s is_sa=%s '
            'totals_count=%s col_groups_count=%s',
            report.id,
            self._is_sin_arrastre(report, options),
            len(all_column_groups_expression_totals) if all_column_groups_expression_totals else 0,
            len(options.get('column_groups') or {}),
        )
        result = super()._dynamic_lines_generator(
            report, options, all_column_groups_expression_totals, warnings
        )
        count = len(result) if isinstance(result, (list, tuple)) else 'generador'
        _logger.warning('SA _dynamic_lines_generator RESULTADO: %s lineas para report.id=%s', count, report.id)
        return result

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
        if not self._is_sin_arrastre(report, options):
            return result
        _logger.warning('SA _get_initial_balance_values: zeroing %s cuentas', len(result))
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
