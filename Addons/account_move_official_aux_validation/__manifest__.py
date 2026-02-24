{
    "name": "Account Move Official vs Auxiliary Accounts Validation",
    "summary": "Bloquea asientos automáticos que mezclen cuentas 1-4 con 5-7 (con confirmación)",
    "version": "18.0.1.1.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "Dflex Argentina SAS",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/official_aux_validation_confirm_wizard_view.xml",
    ],
    "installable": True,
    "application": False,
}
