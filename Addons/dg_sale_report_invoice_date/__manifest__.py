{
    "name": "Ventas - Fecha de facturación en análisis",
    "version": "18.0.1.0.0",
    "summary": "Agrega fecha de facturación al análisis de ventas",
    "description": """
Agrega el campo Fecha de facturación al modelo sale.report para poder
filtrar y agrupar la tabla dinámica de Ventas por fecha de factura,
en lugar de usar solamente la fecha de la orden de venta.
    """,
    "category": "Sales",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["sale", "account"],
    "data": [
        "views/sale_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
