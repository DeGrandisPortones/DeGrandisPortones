# -*- coding: utf-8 -*-
{
    "name": "Sale Global Discount (affects taxes & invoices)",
    "version": "18.0.1.0.3",
    "summary": "Descuento global (%) que reduce base imponible, recalcula impuestos y se refleja en facturas y reportes",
    "category": "Sales",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["sale_management", "account"],
    "data": [
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "reports/sale_report.xml",
        "reports/account_report.xml",
    ],
    "installable": True,
    "application": False,
}
