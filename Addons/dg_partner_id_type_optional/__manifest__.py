# -*- coding: utf-8 -*-
{
    "name": "DG Fix Partner - Tipo de Identificación opcional",
    "version": "18.0.1.0.0",
    "category": "Contacts",
    "summary": "Quita el bloqueo de campo requerido 'Tipo de Identificación' en la ficha de contacto para clientes Consumidor Final sin CUIT.",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["l10n_latam_base"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "application": False,
    "installable": True,
}
