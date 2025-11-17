# -*- coding: utf-8 -*-
{
    "name": "HR Employee Ledger (A/B)",
    "version": "18.0.1.0.0",
    "summary": "Anticipos de sueldos en tipos A (Dinero) y B (Alimentos) con cuenta corriente por empleado",
    "category": "Human Resources",
    "author": "Dflex Argentina SAS",
    "website": "https://example.com",
    "depends": ["hr", "base"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/employee_ledger_views.xml",
        "views/menu.xml",
        "report/receipt_templates.xml",
        "report/report_actions.xml"
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
