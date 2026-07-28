# -*- coding: utf-8 -*-
{
    "name": "DG Bloqueo de CUIT/VAT duplicado en contactos",
    "version": "18.0.1.0.0",
    "category": "Contacts",
    "summary": "Convierte el aviso nativo de 'ya existe un contacto con el mismo CUIT' en un bloqueo real al crear o editar contactos.",
    "description": """
Odoo muestra un aviso no bloqueante cuando el CUIT/VAT de un contacto coincide
con el de otro contacto existente, pero permite guardar igual. Este módulo
agrega una validación que impide crear o guardar un contacto si su CUIT/VAT
coincide con el de otro contacto activo (excluyendo contactos que ya
pertenecen a la misma entidad comercial, como los hijos de una misma empresa).

La validación se puede desactivar puntualmente para procesos automáticos que
necesiten crear contactos con CUIT repetido a propósito (por ejemplo,
sincronizaciones externas) usando el contexto `skip_duplicate_vat_check`.
""",
    "author": "Dflex Argentina SAS",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [],
    "application": False,
    "installable": True,
}
