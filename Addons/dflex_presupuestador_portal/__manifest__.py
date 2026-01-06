# -*- coding: utf-8 -*-
{
    "name": "Dflex Presupuestador Portal",
    "summary": "Presupuestador para Portal/Website (sin licencias internas para distribuidores)",
    "version": "18.0.1.0.0",
    "category": "Sales/Website",
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
        "views/portal_templates.xml",
        "reports/presupuestador_report.xml",
    ],
    "assets": {},
    "application": True,
    "installable": True,
}
