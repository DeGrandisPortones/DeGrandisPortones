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

        gl_root = self.env.ref('account_reports.general_ledger_report', raise_if_not_found=False)
        if not gl_root:
            return super().get_options(previous_options)

        # Devolver opciones de gl_root (report_id del GL oficial) en lugar del standalone.
        # Esto hace que el frontend use gl_root para TODOS los requests siguientes:
        #   - get_report_information_readonly: va directo a gl_root → columnas correctas
        #   - get_expanded_lines_readonly: gl_root permite el expand nativamente → valores visibles
        # Con sin_arrastre=True en previous_options, _custom_options_initializer aplica strict_range
        # (solo período actual, sin saldos de arrastre).
        gl_previous = {**(previous_options or {}), 'sin_arrastre': True}
        options = gl_root.get_options(gl_previous)
        options['sin_arrastre'] = True
        return options
