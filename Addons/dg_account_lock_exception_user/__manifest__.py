# -*- coding: utf-8 -*-
{
    "name": "DG Account Lock Exception by User",
    "summary": "Permite crear excepciones de bloqueo contable para un usuario específico.",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dg_account_lock_exception_user_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
