from odoo import models


class AccountReportNoCarryForward(models.Model):
    _inherit = 'account.report'

    def get_options(self, previous_options=None):
        ref = self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )
        if not ref or self.id != ref.id:
            return super().get_options(previous_options)

        # Delegamos a GL root para que todas las opciones (filtros, fechas,
        # diarios, column_groups) se inicialicen igual que el Mayor nativo.
        gl_root = self.env.ref(
            'account_reports.general_ledger_report',
            raise_if_not_found=False,
        )
        if not gl_root:
            return super().get_options(previous_options)

        options = gl_root.get_options(previous_options)

        # Aplicamos strict_range: solo movimientos del período, sin arrastre
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
