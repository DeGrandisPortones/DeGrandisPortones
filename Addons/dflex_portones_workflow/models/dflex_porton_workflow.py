from odoo import api, models

class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    # NOTA IMPORTANTE:
    # - Los campos x_estado, x_aprob_comercial, x_aprob_planificacion y
    #   x_aprob_administracion ya existen creados con Studio.
    # - Por eso NO los volvemos a definir acá, solamente usamos la lógica Python.

    # -------------------------
    # Acciones de cambio estado
    # -------------------------

    def action_set_acopio(self):
        """Pasar el portón a estado 'acopio'."""
        for rec in self:
            # Si x_estado es selection en Studio, asegurate que exista un valor 'acopio'
            rec.x_estado = "acopio"

    def action_set_pendiente_medicion(self):
        """Marcar el portón como pendiente de medición."""
        for rec in self:
            # Asegurate que el valor exista en la selección de Studio
            rec.x_estado = "pendiente_medicion"

    def action_set_pendiente_modif_comercial(self):
        """Marcar el portón como pendiente de modificación comercial."""
        for rec in self:
            # Asegurate que el valor exista en la selección de Studio
            rec.x_estado = "pendiente_modif_comercial"

    # --------------------------------------
    # Acciones de aprobaciones (3 niveles)
    # --------------------------------------

    def _check_full_approval_and_update_state(self):
        """Si las 3 aprobaciones están en True, pasar a 'preproduccion'."""
        for rec in self:
            if (
                getattr(rec, "x_aprob_comercial", False)
                and getattr(rec, "x_aprob_planificacion", False)
                and getattr(rec, "x_aprob_administracion", False)
            ):
                # De nuevo, asegurate que exista el valor en la selección
                rec.x_estado = "preproduccion"

    def action_aprobar_comercial(self):
        """Marcar aprobación comercial en True."""
        for rec in self:
            if hasattr(rec, "x_aprob_comercial"):
                rec.x_aprob_comercial = True
            rec._check_full_approval_and_update_state()

    def action_aprobar_planificacion(self):
        """Marcar aprobación planificación en True."""
        for rec in self:
            if hasattr(rec, "x_aprob_planificacion"):
                rec.x_aprob_planificacion = True
            rec._check_full_approval_and_update_state()

    def action_aprobar_administracion(self):
        """Marcar aprobación administración en True."""
        for rec in self:
            if hasattr(rec, "x_aprob_administracion"):
                rec.x_aprob_administracion = True
            rec._check_full_approval_and_update_state()
