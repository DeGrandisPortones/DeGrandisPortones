{
    "name": "AR Padrón (AFIP/ARCA) – CUIT Autocomplete",
    "summary": "Completa datos de Contactos desde Padrón (AFIP/ARCA) por CUIT (Argentina)",
    "version": "18.0.1.0.0",
    "category": "Localization/Argentina",
    "author": "Dflex Argentina SAS",
    "website": "https://dflex.com.ar",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "l10n_ar"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml"
    ],
    "external_dependencies": {
        "python": ["zeep"]
    },
    "installable": true,
    "application": false
}