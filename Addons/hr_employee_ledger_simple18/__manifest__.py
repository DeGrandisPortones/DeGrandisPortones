{
    'name': 'HR Employee Ledger (A/B)',
    'version': '18.0.1.0.1',
    'summary': 'Anticipos y cuenta corriente por empleado (Tipos A: Dinero, B: Alimentos)',
    'description': 'Gestión simple de anticipos de sueldos y cuenta corriente por empleado. Incluye recibo PDF.',
    'author': 'Esteban / Dflex Argentina',
    'website': 'https://dflex.com.ar',
    'license': 'LGPL-3',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/employee_ledger_views.xml',
        'report/receipt_templates.xml',
        'report/report_actions.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}