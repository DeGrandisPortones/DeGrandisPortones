from odoo import api, fields, models, _

class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    # Estados posibles del portón
    x_estado = fields.Selection(
        [
            ("acopio", "Acopio"),
            ("pendiente_medicion", "Pendiente de medición"),
            ("pendiente_modif_comercial", "Pendiente de modificación comercial"),
            ("pre_produccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado del portón",
        default="acopio",
        tracking=True,
    )

    # Aprobaciones
    x_aprob_comercial = fields.Boolean(string="Aprobación Comercial", tracking=True)
    x_aprob_planificacion = fields.Boolean(string="Aprobación Planificación", tracking=True)
    x_aprob_administracion = fields.Boolean(string="Aprobación Administración", tracking=True)

    def action_set_acopio(self):
        for record in self:
            record.write({
                "x_estado": "acopio",
                "x_aprob_comercial": False,
                "x_aprob_planificacion": False,
                "x_aprob_administracion": False,
            })

    def action_set_pendiente_medicion(self):
        for record in self:
            record.write({
                "x_estado": "pendiente_medicion",
                "x_aprob_comercial": False,
                "x_aprob_planificacion": False,
                "x_aprob_administracion": False,
            })

    def action_set_pendiente_modif_comercial(self):
        for record in self:
            record.write({
                "x_estado": "pendiente_modif_comercial",
                "x_aprob_comercial": False,
                "x_aprob_planificacion": False,
                "x_aprob_administracion": False,
            })

    def action_set_pre_produccion(self):
        for record in self:
            record.write({
                "x_estado": "pre_produccion",
            })

    def action_set_produccion(self):
        for record in self:
            if record.x_estado != "pre_produccion":
                raise models.ValidationError(
                    _("Solo se puede pasar a Producción si el estado es Pre-producción.")
                )
            if not (record.x_aprob_comercial and record.x_aprob_planificacion and record.x_aprob_administracion):
                raise models.ValidationError(
                    _("Para pasar a Producción, las tres áreas deben haber aprobado: "
                      "Comercial, Planificación y Administración.")
                )
            record.write({
                "x_estado": "produccion",
            })