
{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.0.0",
    "summary": "Adelantos a empleados tipo A (dinero) y tipo B (alimentos). Cuenta corriente por empleado y recibo.",
    "category": "Human Resources",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["hr", "base"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "report/receipt_templates.xml",
        "report/report_actions.xml",
        "views/menu.xml"
    ],
    "installable": True,
    "application": False
}
