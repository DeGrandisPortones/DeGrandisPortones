from odoo import models

class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    # --- Acciones de estado principales ---

    def action_set_acopio(self):
        for record in self:
            record.x_estado = "acopio"

    def action_set_pendiente_medicion(self):
        for record in self:
            record.x_estado = "pendiente_medicion"

    def action_set_pendiente_modif_comercial(self):
        for record in self:
            record.x_estado = "pendiente_modif_comercial"

    # --- Acciones de aprobaciones ---

    def action_toggle_aprob_comercial(self):
        for record in self:
            record.x_aprob_comercial = not bool(record.x_aprob_comercial)

    def action_toggle_aprob_planificacion(self):
        for record in self:
            record.x_aprob_planificacion = not bool(record.x_aprob_planificacion)

    def action_toggle_aprob_administracion(self):
        for record in self:
            record.x_aprob_administracion = not bool(record.x_aprob_administracion)