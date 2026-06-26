# -*- coding: utf-8 -*-

from odoo import models


class AccountGeneralLedgerReportHandler(models.AbstractModel):
    """Force Odoo's standard General Ledger to work without carryover.

    Scope:
    - Only inherits Odoo's standard account_reports General Ledger handler.
    - Does not import, depend on, or modify dg_resumen_cta_cte.

    Expected behavior in Reportes > Libro mayor:
    - Selected date range starts from zero.
    - Previous-period opening/carryover balances are not used.
    - Generated opening balance lines are removed if Odoo still creates them.
    """

    _inherit = "account.general.ledger.report.handler"

    def _is_initial_balance_line(self, line):
        line_id = str(line.get("id") or "").lower()
        parent_id = str(line.get("parent_id") or "").lower()
        name = str(line.get("name") or "").strip().lower()
        caret_options = str(line.get("caret_options") or "").lower()

        if "initial_balance" in line_id or "initial-balance" in line_id:
            return True
        if "initial_balance" in parent_id or "initial-balance" in parent_id:
            return True
        if "initial_balance" in caret_options or "initial-balance" in caret_options:
            return True

        return name in {
            "initial balance",
            "opening balance",
            "balance inicial",
            "saldo inicial",
            "saldo anterior",
            "arrastre",
        }

    def _zero_numeric_values(self, value):
        """Recursively zero numeric values in Odoo initial-balance structures."""
        if isinstance(value, dict):
            return {key: self._zero_numeric_values(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._zero_numeric_values(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._zero_numeric_values(item) for item in value)
        if isinstance(value, (int, float)):
            return 0.0
        return value

    def _get_initial_balance_values(self, *args, **kwargs):
        """Neutralize previous-period balances used by the General Ledger.

        The signature of this helper can vary between Odoo enterprise minor versions,
        so this override intentionally accepts *args/**kwargs.
        """
        values = super()._get_initial_balance_values(*args, **kwargs)
        return self._zero_numeric_values(values)

    def _custom_line_postprocessor(self, *args, **kwargs):
        """Remove generated opening-balance lines as a second safety layer."""
        result = super()._custom_line_postprocessor(*args, **kwargs)

        if isinstance(result, tuple):
            lines = result[0]
            rest = result[1:]
        else:
            lines = result
            rest = None

        if isinstance(lines, list):
            lines = [
                line for line in lines
                if not (isinstance(line, dict) and self._is_initial_balance_line(line))
            ]

        if rest is not None:
            return (lines, *rest)
        return lines
