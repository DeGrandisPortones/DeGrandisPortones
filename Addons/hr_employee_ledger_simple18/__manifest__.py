# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Ledger (A/B)',
    'version': '18.0.1.1.0',
    'summary': 'Cuenta corriente por empleado con anticipos tipo A (dinero) y B (alimentos) + recibo PDF',
    'author': 'Dflex Argentina SAS',
    'category': 'Human Resources',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml',
        'report/receipt_templates.xml',
        'report/report_actions.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
