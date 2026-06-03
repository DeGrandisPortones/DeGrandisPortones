# -*- coding: utf-8 -*-
{
    "name": "DFlex - Importar saldos clientes por grupo reporte",
    "summary": "Importa saldos iniciales de clientes FCA o Interno en un asiento de apertura",
    "version": "18.0.2.0.0",
    "author": "DFLEX Argentina SAS",
    "website": "https://dflex.com.ar",
    "category": "Accounting",
    "license": "LGPL-3",
    "depends": [
        "account",
        "dg_client_sales_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/partner_balance_group_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
