# -*- coding: utf-8 -*-
{
    "name": "DFlex - Importador de Portones (Excel)",
    "summary": "Sube un Excel tal como está y crea fichas de portón con todos los valores. (Solo De Grandis Portones)",
    "version": "18.0.1.2",
    "author": "DFlex Argentina SAS",
    "website": "https://dflex.com",
    "category": "Manufacturing",
    "license": "LGPL-3",
    "depends": ["mrp", "base"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/x_gate_spec_views.xml",
        "views/x_gate_import_batch_views.xml",
        "views/gate_import_wizard_views.xml",
        "views/menuitems.xml"
    ],
    "installable": True,
    "application": False,
}
