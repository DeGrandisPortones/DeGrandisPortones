# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    dg_datos_envio_enabled = fields.Boolean(
        string="Botón para copiar datos de envío en cotizaciones",
        help="Muestra en las cotizaciones de esta empresa un botón que copia los "
        "datos del cliente y de la entrega, para pegarlos en WhatsApp al "
        "coordinar el flete.",
    )
