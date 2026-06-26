from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _get_initial_balance_values(self, report, options, *args, **kwargs):
        """Sin arrastre: obtiene la lista de cuentas del padre pero pone todos los saldos en 0.

        No devuelve {} porque el handler usa este dict también para saber qué
        cuentas mostrar — devolver vacío hace que no aparezca nada.
        """
        result = super()._get_initial_balance_values(report, options, *args, **kwargs)
        return {
            account_id: {
                key: (0.0 if isinstance(val, (int, float)) and not isinstance(val, bool) else val)
                for key, val in account_data.items()
            } if isinstance(account_data, dict) else account_data
            for account_id, account_data in result.items()
        }
