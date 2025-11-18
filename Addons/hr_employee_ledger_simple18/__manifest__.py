{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.0.0",
    "author": "Dflex Argentina SAS",
    "category": "Human Resources",
    "depends": [
        "hr"
    ],
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