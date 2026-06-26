from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _get_initial_balance_values(self, report, options, accounts_results):
        """Sin arrastre: saldo inicial cero en todas las cuentas.

        En Odoo 18 enterprise el método se llama _get_initial_balance_values
        en account.general.ledger.report.handler. Si al instalar el módulo no
        tiene efecto, buscar el nombre correcto en el servidor:
            grep -n "def.*initial_balance" \
                /path/odoo/enterprise/account_reports/models/account_general_ledger.py
        y reemplazar el nombre aquí.
        """
        return {}
