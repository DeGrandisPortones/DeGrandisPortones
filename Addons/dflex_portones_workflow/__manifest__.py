{
    "name": "dflex_portones_workflow",
    "version": "18.0.1.0.0",
    "summary": "Workflow de portones: acopio, medición, pre-producción y aprobaciones",
    "category": "Sales/CRM",
    "author": "Esteban + ChatGPT",
    "license": "LGPL-3",
    "depends": ["sale_management", "mrp"],
    "data": [
        "security/dflex_portones_security.xml",
        "security/ir.model.access.csv",
        "views/dflex_porton_workflow_views.xml"
    ],
    "installable": True,
    "application": False
}