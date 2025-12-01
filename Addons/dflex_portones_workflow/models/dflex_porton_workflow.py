from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        [
            ("acopio", "Acopio"),
            ("para_medir", "Para medir"),
            ("pendiente_modif", "Pendiente de modificaciones"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado",
        default="acopio",
        tracking=True,
    )
    x_aprob_comercial = fields.Boolean("Aprob. Comercial", tracking=True)
    x_aprob_planificacion = fields.Boolean("Aprob. Planificación", tracking=True)
    x_aprob_administracion = fields.Boolean("Aprob. Administración", tracking=True)

    def _reset_aprobaciones(self):
        for rec in self:
            rec.x_aprob_comercial = False
            rec.x_aprob_planificacion = False
            rec.x_aprob_administracion = False

    def action_to_acopio(self):
        for rec in self:
            rec.x_estado = "acopio"
            rec._reset_aprobaciones()

    def action_to_para_medir(self):
        for rec in self:
            rec.x_estado = "para_medir"
            rec._reset_aprobaciones()

    def action_to_pendiente_modif(self):
        for rec in self:
            rec.x_estado = "pendiente_modif"
            rec._reset_aprobaciones()

    def action_to_preproduccion(self):
        for rec in self:
            rec.x_estado = "preproduccion"
            rec._reset_aprobaciones()

    def action_to_produccion(self):
        for rec in self:
            if not (rec.x_aprob_comercial and rec.x_aprob_planificacion and rec.x_aprob_administracion):
                raise UserError(
                    _(
                        "Para pasar a Producción se necesitan las 3 aprobaciones "
                        "(Comercial, Planificación y Administración)."
                    )
                )
            rec.x_estado = "produccion"
            # TODO: acá en el futuro se puede disparar la creación de la orden de fabricación.

    def action_aprobar_comercial(self):
        for rec in self:
            rec.x_aprob_comercial = True

    def action_aprobar_planificacion(self):
        for rec in self:
            rec.x_aprob_planificacion = True

    def action_aprobar_administracion(self):
        for rec in self:
            rec.x_aprob_administracion = True
