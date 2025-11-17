{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.1.0",
    "category": "Human Resources",
    "summary": "Cuenta corriente por empleado con anticipos A (dinero) y B (alimentos) + recibo imprimible",
    "description": "Registra anticipos a empleados (dinero/alimentos), simula cuenta corriente, botón de impresión de recibo y vista de resumen por empleado.",
    "depends": ["hr", "base"],
    "author": "Dflex Argentina SAS / Esteban",
    "website": "https://example.com",
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/menu.xml",
        "views/employee_ledger_views.xml",
        "report/report_actions.xml",
        "report/receipt_templates.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}