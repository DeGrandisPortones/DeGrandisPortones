# -*- coding: utf-8 -*-
{
    "name": "Dflex Presupuestador SPA",
    "summary": "Presupuestador React (Vite) servido por Website/Portal; Odoo 18 como backend",
    "version": "18.0.1.0.0",
    "category": "Website",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": [
        "website",
        "portal",
        "product",
        "account",
    ],
    "data": [
        "security/presupuestador_security.xml",
        "security/ir.model.access.csv",
        "views/backend_views.xml",
        "views/website_templates.xml",
        "reports/presupuestador_report.xml",
    ],
    "assets": {},
    "application": True,
    "installable": True,
}
