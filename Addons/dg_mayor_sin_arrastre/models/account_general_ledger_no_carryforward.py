from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    # DIAGNOSTICO: sin overrides - solo herencia pura
    # Si el reporte muestra datos -> el problema esta en _get_initial_balance_values
    # Si sigue vacio -> el problema esta en la configuracion de la variante
