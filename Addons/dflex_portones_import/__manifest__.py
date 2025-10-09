{
    "name": "DFLEX Portones - Importador (CSV, 1 encabezado)",
    "version": "18.0.3.2.0",
    "summary": "CSV con 1 sola fila de encabezados; datos desde fila 2; omite 'Columna X'; usa 'name' o Nota de Venta; crea campos dinámicos y vista.",
    "author": "Esteban Scalerandi + ChatGPT",
    "website": "https://dflex.com.ar",
    "category": "Manufacturing/Manufacturing",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/porton_views.xml",
        "views/spec_views.xml",
        "views/wizard_views.xml",
        "views/menu.xml"
    ],
    "installable": true,
    "application": false
}