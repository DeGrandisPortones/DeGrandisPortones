from odoo import models, api, _

class DflexPorton(models.Model):
    _inherit = 'x_dflex.porton'

    # ---- Helpers ----
    def _check_all_approvals(self):
        for rec in self:
            if (rec.x_aprob_comercial 
                and rec.x_aprob_planificacion 
                and rec.x_aprob_administracion):
                rec.x_estado = 'produccion'
            return True

    # ---- Acciones de estado principales ----
    def action_set_acopio(self):
        for rec in self:
            rec.x_estado = 'acopio'
        return True

    def action_set_pendiente_medicion(self):
        for rec in self:
            rec.x_estado = 'pendiente_medicion'
        return True

    def action_set_pendiente_modif_comercial(self):
        for rec in self:
            rec.x_estado = 'pendiente_modif_comercial'
        return True

    def action_set_preproduccion(self):
        for rec in self:
            rec.x_estado = 'preproduccion'
        return True

    # ---- Acciones de aprobación ----
    def action_toggle_aprob_comercial(self):
        for rec in self:
            rec.x_aprob_comercial = not bool(rec.x_aprob_comercial)
        self._check_all_approvals()
        return True

    def action_toggle_aprob_planificacion(self):
        for rec in self:
            rec.x_aprob_planificacion = not bool(rec.x_aprob_planificacion)
        self._check_all_approvals()
        return True

    def action_toggle_aprob_administracion(self):
        for rec in self:
            rec.x_aprob_administracion = not bool(rec.x_aprob_administracion)
        self._check_all_approvals()
        return True