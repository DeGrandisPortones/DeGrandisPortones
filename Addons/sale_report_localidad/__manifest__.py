{
    'name': 'Ventas - Localidad en Analisis',
    'version': '18.0.1.0.0',
    'summary': 'Agrega la localidad del cliente al reporte de Ventas',
    'description': """
Agrega el campo Localidad al modelo sale.report para poder
filtrar y agrupar el analisis de ventas por ciudad/localidad del cliente.
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
