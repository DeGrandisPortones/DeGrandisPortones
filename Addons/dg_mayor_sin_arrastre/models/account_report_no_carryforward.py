import logging
from odoo import models

_logger = logging.getLogger(__name__)


class AccountReportNoCarryForward(models.Model):
    _inherit = 'account.report'

    def _sin_arrastre_ref(self):
        return self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )

    def get_options(self, previous_options=None):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_options(previous_options)

        options = super().get_options(previous_options)

        _logger.warning(
            'SA get_options OK: report_id=%s ref.id=%s col_groups_count=%s',
            options.get('report_id'), ref.id, len(options.get('column_groups') or {}),
        )

        col_groups = options.get('column_groups') or {}
        if col_groups:
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

        return options

    def get_lines(self, options):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_lines(options)

        _logger.warning(
            'SA get_lines CALLED: report.id=%s report_id_in_options=%s col_groups=%s',
            self.id, options.get('report_id'), len(options.get('column_groups') or {}),
        )

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if gl_root:
            # Delegar a GL root: tiene line_ids → all_column_groups_expression_totals
            # se computa correctamente → _dynamic_lines_generator genera lineas.
            # sin_arrastre=True permite que _get_initial_balance_values cerce los saldos.
            gl_options = dict(options)
            gl_options['sin_arrastre'] = True
            lines = gl_root.get_lines(gl_options)
            _logger.warning('SA get_lines RESULT: %s lineas', len(lines))
            return lines

        _logger.warning('SA get_lines: no se encontro gl_root, fallback a super()')
        return super().get_lines(options)
