# stock_distributor_delivery_api/__manifest__.py
{
    "name": "Stock Distributor Delivery API",
    "summary": "Marca pedidos para distribuidor y API para completar datos de cliente final",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "depends": ["stock", "sale_stock"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "author": "Esteban Scalerandi",
}
