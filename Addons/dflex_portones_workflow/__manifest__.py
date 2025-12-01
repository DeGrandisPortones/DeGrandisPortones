{
    "name": "DFLEX Portones Workflow",
    "summary": "Workflow y autorizaciones para portones DFLEX",
    "version": "18.0.1.0.0",
    "author": "ChatGPT",
    "license": "LGPL-3",
    "category": "Sales/CRM",
    "depends": [
        "base",
        "sale",
        "mrp"
    ],
    "data": [
        "security/dflex_portones_security.xml",
        "security/ir.model.access.csv",
        "views/dflex_porton_workflow_views.xml",
        "views/menu_views.xml"
    ],
    "installable": True,
    "application": False
}
