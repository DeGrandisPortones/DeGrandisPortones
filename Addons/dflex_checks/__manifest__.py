# -*- coding: utf-8 -*-
{
    "name": "DFlex - Cheques Propios",
    "summary": "Gestión de chequeras y cheques propios físicos/eCheq",
    "version": "18.0.1.2.9",
    "author": "DFLEX Argentina SAS",
    "website": "https://dflex.com.ar",
    "category": "Accounting/Payments",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base",
        "l10n_latam_check",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/check_views.xml",
        "views/account_payment_views.xml",
    ],
    "installable": True,
    "application": False,
}
