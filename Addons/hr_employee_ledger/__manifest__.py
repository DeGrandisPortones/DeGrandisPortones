# -*- coding: utf-8 -*-
{
  'name': 'HR Employee Ledger (RRHH A/B)',
  'version': '18.0.8.0.0',
  'summary': 'Movimientos RRHH A/B + Cierre mensual con vista de balance y asiento global',
  'author': 'Dflex Argentina SAS',
  'license': 'LGPL-3',
  'category': 'Human Resources',
  'depends': ['hr','account'],
  'data': [
    'security/ir.model.access.csv',
    'data/sequence.xml',
    'data/actions_menus.xml',
    'views/hr_employee_ledger_views.xml',
    'views/batch_views.xml',
    'views/batch_wizard_views.xml',
    'views/res_company_views.xml',
    'reports/employee_payment_receipt.xml'
  ],
  'installable': True,
  'application': False,
  'auto_install': False
}
