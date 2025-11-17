{
    "name": "HR Employee Ledger (A/B)",
    "summary": "Cuenta corriente por empleado con anticipos (tipo A dinero / tipo B alimentos) y recibo imprimible.",
    "version": "18.0.1.0.1",
    "category": "Human Resources",
    "depends": ["base", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "views/menu.xml",
        "report/report_actions.xml",
        "report/receipt_templates.xml"
    ],
    "installable": True,
    "license": "LGPL-3"
}