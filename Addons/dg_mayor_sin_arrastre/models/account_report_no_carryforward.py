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

    def get_expanded_lines_readonly(self, *args, **kwargs):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_expanded_lines_readonly(*args, **kwargs)

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if not gl_root:
            return super().get_expanded_lines_readonly(*args, **kwargs)

        # Diagnostico: loguear tipos y claves de cada arg para entender la firma.
        _logger.warning(
            'SA get_expanded_lines_readonly args=%s',
            [(i, type(a).__name__, sorted(a.keys())[:8] if isinstance(a, dict) else repr(a)[:60])
             for i, a in enumerate(args)],
        )

        # Buscar el dict de options. Puede o no tener 'column_groups'.
        # Criterio: cualquier dict que tenga 'report_id' (solo options lo tiene).
        new_args = []
        found_options = False
        for arg in args:
            if isinstance(arg, dict) and 'report_id' in arg:
                arg = {**arg, 'report_id': gl_root.id, 'sin_arrastre': True}
                found_options = True
            new_args.append(arg)

        _logger.warning(
            'SA get_expanded_lines_readonly: found_options=%s delegando a gl_root.id=%s',
            found_options, gl_root.id,
        )
        return gl_root.get_expanded_lines_readonly(*new_args, **kwargs)

    def get_lines(self, options):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_lines(options)

        _logger.warning(
            'SA get_lines CALLED: report.id=%s options_report_id=%s',
            self.id, options.get('report_id'),
        )

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if gl_root:
            gl_options = dict(options)
            gl_options['report_id'] = gl_root.id
            gl_options['sin_arrastre'] = True
            lines = gl_root.get_lines(gl_options)
            _logger.warning('SA get_lines RESULT: %s lineas', len(lines) if lines else 0)
            return lines

        return super().get_lines(options)

    def get_report_information_readonly(self, options):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_report_information_readonly(options)

        _logger.warning(
            'SA get_report_information_readonly CALLED: report.id=%s options_report_id=%s',
            self.id, options.get('report_id'),
        )

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if not gl_root:
            return super().get_report_information_readonly(options)

        # Delegar a GL root con sin_arrastre=True.
        # El frontend usa options['report_id'] para identificar el reporte activo,
        # lo restauramos a self.id para que el ciclo de filtros siga pasando por este override.
        gl_options = dict(options)
        gl_options['report_id'] = gl_root.id
        gl_options['sin_arrastre'] = True

        result = gl_root.get_report_information_readonly(gl_options)

        _logger.warning(
            'SA get_report_information_readonly RESULT: type=%s',
            type(result).__name__,
        )

        # NO restauramos report_id a 25 (standalone).
        # Con report_id=11 (gl_root) en el resultado:
        # - Las acciones de expand van a gl_root => permitidas sin UserError ✓
        # - Proximos get_options van a gl_root con sin_arrastre=True en previous_options
        #   => _custom_options_initializer detecta el flag y aplica strict_range ✓
        # Solo aseguramos que sin_arrastre persiste en las opciones devueltas.
        if isinstance(result, dict) and isinstance(result.get('options'), dict):
            result['options']['sin_arrastre'] = True

        return result
