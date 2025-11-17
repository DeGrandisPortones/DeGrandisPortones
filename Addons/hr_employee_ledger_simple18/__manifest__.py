{
    'name': 'HR Employee Ledger (A/B)',
    'version': '18.0.1.0.0',
    'summary': 'Anticipos de sueldos (dinero/alimentos) con cuenta corriente por empleado y recibo impreso.',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'author': 'Dflex Argentina SAS',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml',
        'report/report_actions.xml',
        'report/receipt_templates.xml'
    ],
    'assets': {},
    'installable': True,
    'application': False
}