# -*- coding: utf-8 -*-
{
    "name": "DFlex - Seguimiento de Compras",
    "summary": "Estados operativos de compras: autorizada, en proceso, recibida y rehacer orden",
    "version": "18.0.1.0.0",
    "author": "DFLEX Argentina SAS",
    "category": "Purchases",
    "license": "LGPL-3",
    "depends": [
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
