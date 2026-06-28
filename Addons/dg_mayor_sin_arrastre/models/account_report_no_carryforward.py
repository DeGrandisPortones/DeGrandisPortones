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

        gl_root = self.env.ref(
            'account_reports.general_ledger_report',
            raise_if_not_found=False,
        )
        if not gl_root:
            return super().get_options(previous_options)

        # Odoo line 2039: if options['report_id'] != self.id → dispatch to variant.
        # Si dejamos report_id=standalone.id en previous_options, gl_root.get_options()
        # redispatcha al standalone → nuestro override → bucle infinito.
        # Solución: eliminar report_id para que gl_root use su propio id como default.
        clean_prev = {k: v for k, v in (previous_options or {}).items() if k != 'report_id'}

        options = gl_root.get_options(clean_prev)

        # Restaurar report_id al standalone para que el frontend siga usando este reporte
        options['report_id'] = ref.id

        # Aplicar strict_range: sólo movimientos del período, sin arrastre
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
