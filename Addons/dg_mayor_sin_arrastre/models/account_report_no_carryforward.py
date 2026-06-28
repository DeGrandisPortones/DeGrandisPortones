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

        # Llamar al super() sobre self (variante), NO sobre gl_root.
        # Como self.id == options['report_id'], Odoo no ejecuta el dispatch
        # de la línea 2039, evitando el loop infinito.
        # La variante hereda line_ids/column_ids del root => data visible.
        options = super().get_options(previous_options)

        # Forzar strict_range por si _custom_options_initializer ya no lo aplicó
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
