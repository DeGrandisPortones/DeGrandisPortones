{
    'name': 'Account Payment Receipt - Modern',
    'summary': 'Modern receipt for customer payments with transfer and e-check details',
    'version': '18.0.1.0.3',
    'category': 'Accounting/Reporting',
    'depends': ['account'],  # No hard dependency on cheques module; guarded via _fields
    'data': ['reports/report_payment_receipt_modern.xml'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'author': 'Esteban + ChatGPT',
}