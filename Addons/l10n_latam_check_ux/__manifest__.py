##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
#
##############################################################################
{
    "name": "Latam Check UX",
    "version": "18.0.2.3.3",
    "category": "Accounting",
    "sequence": 14,
    "summary": "",
    "author": "ADHOC SA",
    "website": "www.adhoc.com.ar",
    "license": "AGPL-3",
    "images": [],
    "depends": [
        "l10n_latam_check",
        "account_ux",
        "account_internal_transfer",
    ],
    "data": [
        "wizards/account_check_action_wizard_view.xml",
        "wizards/checks_to_date_view.xml",
        "views/account_payment_view.xml",
        "views/l10n_latam_check_view.xml",
        "views/third_party_check_filter_action.xml",
        "views/account_journal_view.xml",
        "views/res_partner_view.xml",
        "wizards/l10n_latam_payment_mass_transfer.xml",
        "reports/report_account_transfer.xml",
        "reports/report_checks_to_date.xml",
        "security/ir.model.access.csv",
        "data/recompute_third_party_filter.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": True,
    "application": False,
}
