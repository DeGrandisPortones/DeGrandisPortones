# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        [
            ("acopio", "Acopio"),
            ("pendiente_medicion", "Pendiente de medición"),
            ("pendiente_modificaciones", "Pendiente de modificaciones comerciales"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado del portón",
        default="acopio",
        tracking=True,
    )

    x_aprob_comercial = fields.Boolean(
        string="Aprobado Comercial",
        help="Indica si Comercial aprobó el portón para pasar a producción.",
        tracking=True,
    )
    x_aprob_planificacion = fields.Boolean(
        string="Aprobado Planificación",
        help="Indica si Planificación aprobó el portón para pasar a producción.",
        tracking=True,
    )
    x_aprob_administracion = fields.Boolean(
        string="Aprobado Administración",
        help="Indica si Administración aprobó el portón para pasar a producción.",
        tracking=True,
    )

    def action_iniciar_medicion(self):
        for rec in self:
            rec.x_estado = "pendiente_medicion"

    def action_marcar_pendiente_modif(self):
        for rec in self:
            rec.x_estado = "pendiente_modificaciones"

    def action_marcar_acopio(self):
        for rec in self:
            rec.x_estado = "acopio"

    def action_marcar_preproduccion(self):
        for rec in self:
            rec.x_estado = "preproduccion"

    def action_marcar_produccion(self):
        for rec in self:
            rec.x_estado = "produccion"

    @api.constrains("x_estado", "x_aprob_comercial", "x_aprob_planificacion", "x_aprob_administracion")
    def _check_aprobaciones_para_produccion(self):
        for rec in self:
            if rec.x_estado == "produccion":
                if not (rec.x_aprob_comercial and rec.x_aprob_planificacion and rec.x_aprob_administracion):
                    raise models.ValidationError(
                        "No se puede pasar a Producción sin las 3 aprobaciones:
"
                        "- Comercial
"
                        "- Planificación
"
                        "- Administración"
                    )
