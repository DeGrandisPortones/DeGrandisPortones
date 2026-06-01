{
    "name": "Resumen Cta Cte",
    "version": "18.0.1.5.0",
    "category": "Accounting/Reporting",
    "summary": "Resumen de cuenta corriente de clientes separado por FCA e Internas",
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": [
        "account",
        "dg_client_sales_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/report_account_statement_templates.xml",
        "report/report_actions.xml",
        "views/account_statement_wizard_views.xml",
        "views/account_statement_line_views.xml",
        "views/account_statement_summary_views.xml",
    ],
    "installable": True,
    "application": False,
}
