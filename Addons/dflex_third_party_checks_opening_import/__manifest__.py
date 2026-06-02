# -*- coding: utf-8 -*-
{
    "name": "DFlex - Importar cheques de terceros en cartera",
    "summary": "Importa cheques de terceros iniciales contra Capital integrado usando el circuito nativo de cheques",
    "version": "18.0.1.0.0",
    "author": "DFLEX Argentina SAS",
    "website": "https://dflex.com.ar",
    "category": "Accounting/Payments",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_latam_check",
        "l10n_latam_check_ux",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/third_party_checks_opening_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
