from odoo import models


class AccountGeneralLedgerReportHandlerNoCarryForward(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _is_sin_arrastre(self, report, options=None):
        ref = self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )
        if not ref:
            return False
        if report and report.id == ref.id:
            return True
        if options and options.get('sin_arrastre'):
            return True
        if options and options.get('report_id') == ref.id:
            return True
        return False

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        is_sa = self._is_sin_arrastre(report, options) or \
                bool((previous_options or {}).get('sin_arrastre'))
        if not is_sa:
            return

        options['sin_arrastre'] = True

        # El Libro Mayor estandar fuerza unfold_all=True al entrar en print_mode
        # cuando no hay ninguna linea desplegada. XLSX usa print_mode, por eso un
        # reporte colapsado terminaba exportandose completamente detallado.
        #
        # Para Mayor Sin Arrastre preservamos exactamente el estado de expansion
        # que llega desde la pantalla:
        #   - sin cuentas desplegadas -> resumen solamente
        #   - cuentas desplegadas manualmente -> solo esas quedan desplegadas
        #   - "Desplegar todo" activo -> se exporta todo desplegado
        if self._context.get('print_mode'):
            options['unfold_all'] = bool((previous_options or {}).get('unfold_all', False))

        col_groups = options.get('column_groups') or {}
        if not col_groups:
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

    def _get_initial_balance_values(self, report, account_ids, options):
        result = super()._get_initial_balance_values(report, account_ids, options)
        if not self._is_sin_arrastre(report, options):
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
