{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.2.0",
    "summary": "Adelantos y cuenta corriente por empleado (Tipo A/B) con recibo PDF",
    "category": "Human Resources/Employees",
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "report/report_actions.xml",
        "report/receipt_templates.xml"
    ],
    "installable": true,
    "application": false,
    "license": "LGPL-3"
}