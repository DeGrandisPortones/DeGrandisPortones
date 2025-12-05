{
    "name": "Dflex Porton Sync",
    "version": "18.0.6.0.0",
    "depends": ["sale"],
    "author": "Dflex Argentina SAS",
    "category": "Sales",
    "data": [
        "security/ir.model.access.csv",
        "views/porton_views.xml",
        "views/sql_quotation_wizard_views.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "dflex_porton_sync/static/src/js/porton_formula_widget.js",
            "dflex_porton_sync/static/src/xml/porton_formula_widget.xml"
        ]
    },
    "installable": true,
    "application": false
}