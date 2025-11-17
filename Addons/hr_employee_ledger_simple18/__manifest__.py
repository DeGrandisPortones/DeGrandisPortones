# -*- coding: utf-8 -*-
{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.0.0",
    "summary": "Cuenta corriente de empleados con anticipos de sueldos Tipo A (dinero) y Tipo B (alimentos)",
    "category": "Human Resources",
    "author": "Dflex Argentina SAS",
    "website": "https://example.com",
    "license": "OPL-1",
    "depends": ["hr", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "report/receipt_templates.xml",
        "report/report_actions.xml",
        "views/menu.xml"
    ],
    "installable": True,
    "application": False,
}