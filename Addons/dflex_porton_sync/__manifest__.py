{
    "name": "Dflex Porton Sync",
    "version": "18.0.7.0.1",
    "depends": ["sale"],
    "author": "Dflex Argentina SAS",
    "category": "Sales",
    "assets": {
        "web.assets_backend": [
            "dflex_porton_sync/static/src/js/porton_formula_widget.js",
            "dflex_porton_sync/static/src/xml/porton_formula_widget.xml",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/porton_views.xml",
        "views/sql_quotation_wizard_views.xml"
    ],
    "installable": True,
    "application": False
}