# -*- coding: utf-8 -*-
{
    "name": "DG Sync listas de precios desde principal",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Actualiza listas de precios derivadas desde una lista principal con descuento porcentual.",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["product", "sale_management"],
    "data": [
        "views/product_pricelist_views.xml",
        "data/ir_cron.xml",
    ],
    "application": False,
    "installable": True,
}
