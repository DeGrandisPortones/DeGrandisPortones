# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    # Al instalar, activar el botón solo en Vert Deco Cercos. Después se puede
    # prender/apagar por empresa desde la ficha de la empresa.
    env["res.company"].search([("name", "=ilike", "Vert Deco Cercos")]).write(
        {"dg_datos_envio_enabled": True}
    )
