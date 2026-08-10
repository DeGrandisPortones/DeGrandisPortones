# -*- coding: utf-8 -*-
{
    "name": "DG Facturación - Filtro por Etiquetas de Cliente",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Permite filtrar y agrupar facturas/notas de crédito por las etiquetas del cliente/proveedor.",
    "description": """
Agrega el campo Etiquetas de Cliente (etiquetas del contacto, campo Tags de
res.partner) a account.move y lo expone en la búsqueda de Facturación
(Facturas de Clientes, Notas de Crédito, Facturas de Proveedores, etc.):

- Como campo de búsqueda rápida (podés escribir/seleccionar una etiqueta).
- Como opción "Agrupar por > Etiqueta de Cliente".
- Como columna opcional (oculta por defecto) en la lista.

Las etiquetas de contacto no dependen de la compañía, por lo que el filtro
queda disponible igual para todas las empresas de la base (Dflex, Vert, etc.).
    """,
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
