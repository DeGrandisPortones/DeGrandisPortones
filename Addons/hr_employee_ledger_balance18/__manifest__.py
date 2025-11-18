{
    "name": "HR Employee Ledger Balance (CC View)",
    "version": "18.0.1.0.0",
    "author": "Dflex Argentina SAS",
    "category": "Human Resources",
    "depends": ["hr", "hr_employee_ledger_simple18"],
    "data": [
        "security/ir.model.access.csv",
        "views/balance_views.xml",
        "views/menu.xml",
        "views/employee_button_inherit.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}