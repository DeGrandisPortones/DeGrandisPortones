{
    "name": "HR Employee Ledger (A/B)",
    "summary": "Cuenta corriente por empleado con anticipos tipo A (dinero) y B (alimentos) + recibo PDF",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "report/report_actions.xml",
        "report/receipt_templates.xml"
    ],
    "installable": True,
    "application": False
}