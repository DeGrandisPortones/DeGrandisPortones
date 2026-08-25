# -*- coding: utf-8 -*-
{
    "name": "DG Document Reports",
    "version": "18.0.1.0.0",
    "author": "Dflex Argentina SAS",
    "category": "Accounting",
    "summary": "Reportes PDF alternativos para documentos contables de DFLEX",
    "license": "LGPL-3",
    "depends": ["sale", "l10n_ar_edi", "l10n_ar_ux"],
    "data": [
        "reports/report_actions.xml",
        "reports/report_invoice_dg.xml"
    ],
    "assets": {
        "web.report_assets_common": [
            "dg_document_reports/static/src/css/report_invoice_dg.css",
        ],
    },
    "installable": True,
    "application": False
}
