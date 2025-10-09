{
    "name": "DFLEX Portones - Importador",
    "version": "18.0.3.0.4",
    "summary": "Importa PRINCIPAL desde XLSX/XLS o CSV; fila1+fila2=encabezados; datos desde fila3; omite 'Columna X'; crea campos x_.",
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