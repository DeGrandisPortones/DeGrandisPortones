# -*- coding: utf-8 -*-
{
    "name": "DG Datos de envío en cotizaciones",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "summary": "Muestra la dirección de entrega en la cotización y agrega un botón para copiar los datos de envío para coordinar el flete por WhatsApp.",
    "description": """
1) Dirección de entrega distinta de la fiscal
   Odoo ya permite una dirección de entrega distinta (contacto hijo del cliente
   de tipo "Dirección de entrega"), pero en la cotización solo muestra el nombre
   del contacto: como coincide con el del cliente, parece que facturación y
   entrega fueran la misma. Este módulo muestra la dirección debajo del campo
   "Dirección de entrega" para que se vea a dónde se envía.

2) Botón para copiar los datos de envío
   En las cotizaciones de las empresas que lo tengan activado (ficha de la
   empresa > "Botón para copiar datos de envío en cotizaciones"), agrega el
   renglón "Datos de envío" con un botón "Copiar" que copia al portapapeles:

       Nombre completo / Cuit o DNI / mail / Telefono   (del cliente)
       Dirección / Codigo Postal                        (de la dirección de entrega)
       Cantidad                                         (solo productos físicos)

   Las notas de las líneas no se copian porque suelen tener condiciones de pago.
   Al instalar se activa solo para Vert Deco Cercos.
""",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "application": False,
    "installable": True,
}
