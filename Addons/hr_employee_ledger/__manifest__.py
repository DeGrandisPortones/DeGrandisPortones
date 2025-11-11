# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Ledger (A/B simple)',
    'version': '18.0.4.0.0',
    'summary': 'Cta. cte. empleados A/B con pseudo-movimientos y cierre por lote editable',
    'author': 'Dflex Argentina SAS / Esteban Scalerandi',
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