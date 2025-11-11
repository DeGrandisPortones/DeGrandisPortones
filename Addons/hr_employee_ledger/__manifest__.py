{
    'name': 'HR Employee Ledger',
    'version': '18.0.3.1.0',
    'summary': 'Cuenta corriente de empleados (A/B), cierre por lote editable y recibo PDF.',
    'author': 'ChatGPT Assistant',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'depends': ['hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/hr_employee_ledger_views.xml',
        'views/batch_wizard_views.xml',
        'views/batch_views.xml',
        'views/res_company_views.xml',
        'reports/employee_payment_receipt.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False
}