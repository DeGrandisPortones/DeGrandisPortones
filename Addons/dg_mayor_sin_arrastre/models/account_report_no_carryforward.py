from odoo import models


class AccountReportNoCarryForward(models.Model):
    _inherit = 'account.report'

    def _sin_arrastre_ref(self):
        return self.env.ref(
            'dg_mayor_sin_arrastre.general_ledger_no_carryforward_report',
            raise_if_not_found=False,
        )

    def _is_sin_arrastre_report(self, options=None):
        ref = self._sin_arrastre_ref()
        return bool(
            ref
            and (
                self.id == ref.id
                or (options or {}).get('sin_arrastre')
            )
        )

    def get_options(self, previous_options=None):
        ref = self._sin_arrastre_ref()
        if not ref or self.id != ref.id:
            return super().get_options(previous_options)

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if not gl_root:
            return super().get_options(previous_options)

        # Devolver opciones de gl_root (report_id del GL oficial) en lugar del standalone.
        # Esto hace que el frontend use gl_root para TODOS los requests siguientes:
        #   - get_report_information_readonly: va directo a gl_root -> columnas correctas
        #   - get_expanded_lines_readonly: gl_root permite el expand nativamente -> valores visibles
        # Con sin_arrastre=True en previous_options, _custom_options_initializer aplica strict_range
        # (solo periodo actual, sin saldos de arrastre).
        gl_previous = {**(previous_options or {}), 'sin_arrastre': True}
        options = gl_root.get_options(gl_previous)
        options['sin_arrastre'] = True
        return options

    def export_to_xlsx(self, options, response=None):
        """Exportar respetando exactamente el estado de expansion de la pantalla.

        El Libro Mayor estandar de Odoo activa ``unfold_all`` en print_mode cuando
        ``unfolded_lines`` esta vacio. El export XLSX usa print_mode, de modo que
        una pantalla completamente colapsada termina exportandose con todas las
        cuentas abiertas.

        Para Mayor Sin Arrastre, cuando la pantalla esta colapsada agregamos un
        id centinela que nunca coincide con una linea real. Asi Odoo entiende que
        no debe ejecutar su auto-unfold de impresion, pero ninguna cuenta queda
        realmente desplegada. Si hay cuentas desplegadas, se conserva la lista
        original; y si el usuario activo "Desplegar todo", se conserva unfold_all.
        """
        if not self._is_sin_arrastre_report(options):
            return super().export_to_xlsx(options, response=response)

        export_options = dict(options or {})
        export_options['sin_arrastre'] = True

        if not export_options.get('unfold_all') and not export_options.get('unfolded_lines'):
            export_options['unfolded_lines'] = ['__dg_mayor_sin_arrastre_keep_folded__']

        return super().export_to_xlsx(export_options, response=response)
