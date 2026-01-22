# -*- coding: utf-8 -*-
{
    "name": "Dflex - Financiamiento Taca Taca (Recargo por Cuotas)",
    "version": "18.0.1.0.8",
    "category": "Sales/Sales",
    "summary": "Aplica recargo porcentual por cuotas según plan/tarjeta, recalculando el precio unitario por línea.",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "data/ir_config_parameter.xml",
        "security/ir.model.access.csv",
        "data/financing_data.xml",
        "views/sale_financing_views.xml",
        "views/sale_order_views.xml",
    ],
    "application": False,
    "installable": True,
}
