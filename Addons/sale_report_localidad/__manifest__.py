{
    'name': 'Ventas - Localidad y Provincia en Analisis',
    'version': '18.0.1.1.0',
    'summary': 'Agrega Localidad y Provincia del cliente al reporte de Ventas',
    'description': """
Agrega el campo Localidad al modelo sale.report para poder
filtrar y agrupar el analisis de ventas por ciudad/localidad del cliente.
Tambien expone el estado del cliente con la etiqueta Provincia.
    """,
    'category': 'Sales',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'depends': ['sale'],
    'data': [
        'views/sale_report_views.xml',
    ],
    'installable': True,
    'application': False,
}
