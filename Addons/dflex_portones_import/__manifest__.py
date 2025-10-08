{
    "name": "DFLEX Portones - Importador (Dinámico por columnas)",
    "version": "18.0.2.0.0",
    "summary": "Importa hoja PRINCIPAL; genera campos x_ a partir de fila 1 y 2; datos desde fila 3; omite columnas 'Columna X'.",
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
    "assets": {},
    "installable": true,
    "application": false
}