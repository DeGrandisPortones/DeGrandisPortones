{
    "name": "Reporte de Proveedores por Diario",
    "version": "18.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Reporte de deuda con proveedores separado por compras oficiales, internas y saldos iniciales",
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "views/dg_supplier_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
