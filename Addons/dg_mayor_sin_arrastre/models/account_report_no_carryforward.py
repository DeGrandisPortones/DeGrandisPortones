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
            'SA get_options: report_id=%s ref.id=%s col_groups_keys=%s',
            options.get('report_id'), ref.id, list((options.get('column_groups') or {}).keys()),
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

        gl_root = self.root_report_id
        _logger.warning(
            'SA get_lines: self.id=%s ref.id=%s gl_root=%s options_report_id=%s col_groups=%s',
            self.id, ref.id, gl_root.id if gl_root else None,
            options.get('report_id'),
            list((options.get('column_groups') or {}).keys()),
        )

        if gl_root:
            # Forzar report_id al root para que get_lines use sus line_ids.
            # sin_arrastre=True permite que _get_initial_balance_values detecte el modo.
            gl_options = dict(options)
            gl_options['report_id'] = gl_root.id
            gl_options['sin_arrastre'] = True
            lines = gl_root.get_lines(gl_options)
            _logger.warning('SA get_lines resultado: %s lineas', len(lines))
            return lines

        return super().get_lines(options)
