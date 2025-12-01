from odoo import models

class DflexPortonWorkflow(models.Model):
    """Extiende el modelo Studio x_dflex.porton para manejar estados y aprobaciones.

    Este módulo asume que el modelo `x_dflex.porton` ya existe en la base
    (creado con Studio) y que tiene al menos estos campos:
      * x_estado (selection o char)
      * x_aprob_comercial (boolean)
      * x_aprob_planificacion (boolean)
      * x_aprob_administracion (boolean)
    """

    _inherit = "x_dflex.porton"

    # ----- Acciones de estado simples -----

    def action_set_acopio(self):
        for rec in self:
            # valor de estado esperado para "Acopio"
            rec.x_estado = "acopio"

    def action_set_pendiente_medicion(self):
        for rec in self:
            # valor de estado esperado para "Pendiente de medición"
            rec.x_estado = "pendiente_medicion"

    def action_set_pendiente_modif_comercial(self):
        for rec in self:
            # valor de estado esperado para "Pendiente de modificación comercial"
            rec.x_estado = "pendiente_modif_comercial"

    # ----- Acciones de aprobación -----

    def action_aprobar_comercial(self):
        for rec in self:
            if hasattr(rec, "x_aprob_comercial"):
                rec.x_aprob_comercial = True
            rec._check_all_aprobaciones_to_preproduccion()

    def action_aprobar_planificacion(self):
        for rec in self:
            if hasattr(rec, "x_aprob_planificacion"):
                rec.x_aprob_planificacion = True
            rec._check_all_aprobaciones_to_preproduccion()

    def action_aprobar_administracion(self):
        for rec in self:
            if hasattr(rec, "x_aprob_administracion"):
                rec.x_aprob_administracion = True
            rec._check_all_aprobaciones_to_preproduccion()

    # ----- Helper -----

    def _check_all_aprobaciones_to_preproduccion(self):
        """Si las 3 aprobaciones están en True, pasa el estado a 'preproduccion'."""
        for rec in self:
            ok_com = getattr(rec, "x_aprob_comercial", False)
            ok_pla = getattr(rec, "x_aprob_planificacion", False)
            ok_adm = getattr(rec, "x_aprob_administracion", False)

            if ok_com and ok_pla and ok_adm:
                rec.x_estado = "preproduccion"
