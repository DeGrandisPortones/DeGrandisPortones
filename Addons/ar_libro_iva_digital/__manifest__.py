# -*- coding: utf-8 -*-
{
    "name": "AR - Libro IVA Digital (Compras/Ventas)",
    "summary": "Genera TXT AFIP: CBTE y ALICUOTAS para Compras/Ventas",
    "version": "18.0.1.0.3",
    "license": "AGPL-3",
    "category": "Accounting/Localizations",
    "author": "DeGrandisPortones",
    "depends": ["account", "l10n_ar"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/libro_iva_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
}
