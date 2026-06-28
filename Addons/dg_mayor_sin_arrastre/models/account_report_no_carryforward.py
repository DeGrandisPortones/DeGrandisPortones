from odoo import models


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

        # Delegar al GL root para que compute all_column_groups_expression_totals
        # desde sus line_ids (no vacios). Sin esto, _dynamic_lines_generator recibe
        # {} y devuelve cero lineas. strict_range ya esta en options['column_groups']
        # y _get_initial_balance_values detecta sin_arrastre via options['report_id'].
        gl_root = self.root_report_id
        if gl_root:
            return gl_root.get_lines(options)
        return super().get_lines(options)
