from odoo import api, fields, models, _

class DflexPortonWorkflow(models.Model):
    _inherit = 'x_dflex.porton'

    # No redefinimos los campos Studio (x_estado, x_aprob_*) para evitar conflictos.
    # Solo implementamos acciones de workflow que los actualizan.

    def _set_estado(self, estado):
        for record in self:
            record.x_estado = estado

    # --- Estados principales ---

    def action_set_acopio(self):
        for record in self:
            record._set_estado('acopio')
        return True

    def action_set_pendiente_medicion(self):
        for record in self:
            record._set_estado('pendiente_medicion')
        return True

    def action_set_pendiente_modif_comercial(self):
        for record in self:
            record._set_estado('pendiente_modif_comercial')
        return True

    def action_set_preproduccion(self):
        for record in self:
            record._set_estado('preproduccion')
        return True

    # --- Aprobaciones ---

    def action_aprobar_comercial(self):
        for record in self:
            record.x_aprob_comercial = True
        return True

    def action_aprobar_planificacion(self):
        for record in self:
            record.x_aprob_planificacion = True
        return True

    def action_aprobar_administracion(self):
        for record in self:
            record.x_aprob_administracion = True
        return True

    def action_reset_aprobaciones(self):
        for record in self:
            record.x_aprob_comercial = False
            record.x_aprob_planificacion = False
            record.x_aprob_administracion = False
        return True