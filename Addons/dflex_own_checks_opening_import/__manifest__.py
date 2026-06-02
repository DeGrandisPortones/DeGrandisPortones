# -*- coding: utf-8 -*-
{
    "name": "DFlex - Importar cheques propios en circulacion",
    "summary": "Carga inicial segura de cheques propios en circulacion contra Capital integrado",
    "version": "18.0.1.0.0",
    "author": "DFLEX Argentina SAS",
    "category": "Accounting/Payments",
    "license": "LGPL-3",
    "depends": [
        "account",
        "dflex_checks",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dflex_own_check_opening_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
