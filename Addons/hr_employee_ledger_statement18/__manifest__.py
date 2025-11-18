{
    "name": "HR Employee Ledger - Statement Wizard",
    "version": "18.0.1.0.0",
    "author": "Dflex Argentina SAS",
    "category": "Human Resources",
    "depends": ["hr", "hr_employee_ledger_simple18"],
    "data": [
        "security/ir.model.access.csv",
        "actions/actions.xml",
        "views/wizard_views.xml",
        "views/move_views.xml",
        "menus/menu.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}