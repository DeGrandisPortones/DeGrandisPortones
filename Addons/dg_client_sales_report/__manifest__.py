{
    "name": "Reporte de Clientes por Diario",
    "version": "18.0.1.2.1",
    "category": "Accounting/Reporting",
    "summary": "Reporte de deuda de clientes separado por ventas oficiales, internas y saldos iniciales",
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/dg_client_sales_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
