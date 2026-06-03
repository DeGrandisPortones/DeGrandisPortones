# -*- coding: utf-8 -*-
{
    "name": "DFlex - Importar saldos iniciales de contactos",
    "summary": "Importa saldos iniciales de clientes separados por FCA e Interno contra Capital integrado",
    "version": "18.0.1.1.1",
    "author": "DFLEX Argentina SAS",
    "website": "https://dflex.com.ar",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/partner_balance_opening_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
