# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Ledger (A/B)',
    'summary': 'Anticipos A/B y cuenta corriente por empleado con recibo',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'author': 'Esteban + ChatGPT',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml',
        'views/employee_views.xml',
        'report/employee_advance_receipt_report.xml',
        'report/employee_advance_receipt_templates.xml',
    ],
    'installable': True,
    'application': True,
}
