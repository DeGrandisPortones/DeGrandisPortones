# -*- coding: utf-8 -*-
{
    "name": "Dflex - Financiamiento Taca Taca (Recargo por Cuotas)",
    "version": "18.0.1.1.3",
    "category": "Sales/Sales",
    "summary": "Aplica recargo por cuotas y permite emitir una comparativa de financiación en PDF.",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "data/ir_config_parameter.xml",
        "security/ir.model.access.csv",
        "data/financing_data.xml",
        "views/sale_financing_views.xml",
        "views/sale_order_views.xml",
        "reports/report_saleorder_financing_comparison.xml",
    ],
    "application": False,
    "installable": True,
}
