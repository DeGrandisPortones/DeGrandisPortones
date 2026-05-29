{
    "name": "Reporte de Clientes por Diario",
    "version": "18.0.1.1.2",
    "category": "Accounting/Reporting",
    "summary": "Reporte de clientes separado por ventas oficiales, internas y saldos iniciales",
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dg_client_sales_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
