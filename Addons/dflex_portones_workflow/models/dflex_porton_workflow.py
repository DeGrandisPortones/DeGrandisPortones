from odoo import models, _
from odoo.exceptions import UserError


class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    # NOTA IMPORTANTE:
    # No definimos los campos x_estado, x_aprob_comercial,
    # x_aprob_planificacion ni x_aprob_administracion porque
    # ya existen creados con Studio en el modelo x_dflex.porton.

    # ---- helpers internos ----
    def _check_group(self, xmlid):
        """Lanza error si el usuario no pertenece al grupo indicado."""
        if not self.env.user.has_group(xmlid):
            raise UserError(_("No tiene permisos para realizar esta operación."))
        return True

    # ---- Transiciones de estado principales ----
    def action_set_acopio(self):
        """Marcar el portón como 'acopio'."""
        self._check_group("dflex_portones_workflow.group_dflex_comercial")
        for rec in self:
            if hasattr(rec, "x_estado"):
                rec.x_estado = "acopio"
        return True

    def action_set_pendiente_medicion(self):
        """Marcar el portón como pendiente de medición."""
        self._check_group("dflex_portones_workflow.group_dflex_comercial")
        for rec in self:
            if hasattr(rec, "x_estado"):
                rec.x_estado = "pendiente_medicion"
        return True

    def action_set_pendiente_modif_comercial(self):
        """Marcar el portón como pendiente de modificaciones comerciales."""
        self._check_group("dflex_portones_workflow.group_dflex_comercial")
        for rec in self:
            if hasattr(rec, "x_estado"):
                rec.x_estado = "pendiente_modif_comercial"
        return True

    # ---- Aprobaciones ----
    def action_aprobar_comercial(self):
        self._check_group("dflex_portones_workflow.group_dflex_comercial")
        for rec in self:
            if hasattr(rec, "x_aprob_comercial"):
                rec.x_aprob_comercial = True
        return True

    def action_aprobar_planificacion(self):
        self._check_group("dflex_portones_workflow.group_dflex_planificacion")
        for rec in self:
            if hasattr(rec, "x_aprob_planificacion"):
                rec.x_aprob_planificacion = True
        return True

    def action_aprobar_administracion(self):
        self._check_group("dflex_portones_workflow.group_dflex_administracion")
        for rec in self:
            if hasattr(rec, "x_aprob_administracion"):
                rec.x_aprob_administracion = True
        return True
