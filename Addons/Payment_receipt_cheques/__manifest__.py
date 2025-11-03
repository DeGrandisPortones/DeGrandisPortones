{
    "name": "Payment Receipt - Cheques",
    "summary": "Add check lines to customer payments and print them on the Payment Receipt",
    "version": "18.0.1.0.1",
    "category": "Accounting/Accounting",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
        "reports/report_payment_receipt_checks.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "author": "Esteban + ChatGPT"
}