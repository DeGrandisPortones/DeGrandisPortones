from odoo import models, fields
from odoo.exceptions import UserError


class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        [
            ("acopio", "Acopio"),
            ("pendiente_medicion", "Pendiente de medición"),
            ("pendiente_modif_comercial", "Pendiente de modificación comercial"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado del portón",
        default="acopio",
        tracking=True,
    )

    x_aprob_comercial = fields.Boolean(string="Aprobación Comercial")
    x_aprob_planificacion = fields.Boolean(string="Aprobación Planificación")
    x_aprob_administracion = fields.Boolean(string="Aprobación Administración")

    def action_set_acopio(self):
        for rec in self:
            rec.x_estado = "acopio"

    def action_set_pendiente_medicion(self):
        for rec in self:
            rec.x_estado = "pendiente_medicion"

    def action_set_pendiente_modif_comercial(self):
        for rec in self:
            rec.x_estado = "pendiente_modif_comercial"

    def action_set_preproduccion(self):
        for rec in self:
            rec.x_estado = "preproduccion"

    def action_set_produccion(self):
        for rec in self:
            if not (
                rec.x_aprob_comercial
                and rec.x_aprob_planificacion
                and rec.x_aprob_administracion
            ):
                raise UserError(
                    "No se puede pasar a Producción sin las tres aprobaciones "
                    "(Comercial, Planificación y Administración)."
                )
            rec.x_estado = "produccion"
