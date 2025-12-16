# -*- coding: utf-8 -*-
{
    "name": "DFlex - Cheques Propios",
    "summary": "Gestión de chequeras y cheques propios (físicos y eCheq)",
    "version": "18.0.1.0.1",
    "author": "DFLEX Argentina SAS",
    "website": "https://dflex.com.ar",
    "category": "Accounting/Payments",
    "license": "LGPL-3",
    "depends": ["account", "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/check_views.xml",
        "views/account_payment_views.xml"
    ],
    "installable": True,
    "application": False
}
