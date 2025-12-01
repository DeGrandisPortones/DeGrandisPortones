# -*- coding: utf-8 -*-
{
    "name": "DFLEX Portones - Workflow",
    "summary": "Estados y aprobaciones del portón (Acopio / Producción)",
    "version": "1.0.0",
    "author": "Esteban + ChatGPT",
    "license": "LGPL-3",
    "depends": ["base", "sale", "x_portones"],  # x_portones = módulo estándar donde está el modelo x_dflex.porton
    "data": [
        "security/dflex_portones_security.xml",
        "views/dflex_porton_workflow_views.xml",
        "views/dflex_porton_menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
