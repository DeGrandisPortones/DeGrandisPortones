{
    "name": "HR Employee Ledger",
    "version": "18.0.2.0.0",
    "summary": "Cuenta corriente de empleados (A/B) y cierre mensual contable agregado.",
    "author": "ChatGPT Assistant",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["hr", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/hr_employee_ledger_views.xml",
            "views/batch_views.xml",
        "views/batch_wizard_views.xml",
        "views/res_config_settings_views.xml"
    ],
    "installable": True,
    "application": False
}