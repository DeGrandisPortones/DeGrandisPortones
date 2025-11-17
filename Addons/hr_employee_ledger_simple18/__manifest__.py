{
    'name': 'HR Employee Ledger (A/B)',
    'version': '18.0.1.0.0',
    'summary': 'Cuenta corriente de empleados con anticipos tipo A (Dinero) y B (Alimentos)',
    'category': 'Human Resources',
    'author': 'ChatGPT',
    'maintainers': ['ChatGPT'],
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'report/receipt_templates.xml',
        'report/report_actions.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml'
    ],
    'installable': True,
    'application': False
}
