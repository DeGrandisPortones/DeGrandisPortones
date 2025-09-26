{
    "name": "AR - Libro IVA Digital (TXT)",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "category": "Accounting/Localizations",
    "depends": [
        "account", "l10n_ar", "l10n_ar_reports",
        "l10n_ar_base_vat", "l10n_ar_invoice"
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/vat_ledger_wizard_views.xml",
        "views/vat_ledger_menu.xml",
    ],
    "installable": True,
}
