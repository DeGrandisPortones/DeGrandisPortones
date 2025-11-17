
# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Ledger (A/B)',
    'summary': 'Anticipos y cuenta corriente por empleado (tipos A/B)',
    'version': '18.0.1.3',
    'author': 'ChatGPT',
    'website': 'https://example.com',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'report/receipt_templates.xml',
        'report/report_actions.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
