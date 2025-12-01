# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class DflexPortonWorkflow(models.Model):
    """Extiende el modelo del portón de Studio (`x_dflex.porton`).

    IMPORTANTE:
    - El nombre del modelo debe coincidir EXACTO con el que ves en Studio.
    - En tu base de datos, por los errores que mostrás, el modelo se llama
      `x_dflex.porton`, por eso lo usamos en `_inherit`.
    """

    _inherit = "x_dflex.porton"

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _set_estado(self, nuevo_estado):
        for rec in self:
            rec.x_estado = nuevo_estado

    # ------------------------------------------------------------------
    # Acciones de estado principal
    # ------------------------------------------------------------------
    def action_set_acopio(self):
        """Marcar el portón como ACOPIO."""
        _logger.info("DFLEX WORKFLOW: action_set_acopio sobre ids %s", self.ids)
        self._set_estado("acopio")
        return True

    def action_set_pendiente_medicion(self):
        """Marcar el portón como pendiente de medición."""
        _logger.info("DFLEX WORKFLOW: action_set_pendiente_medicion sobre ids %s", self.ids)
        self._set_estado("pendiente_medicion")
        return True

    def action_set_pendiente_modif_comercial(self):
        """Marcar el portón como pendiente de modificación comercial."""
        _logger.info("DFLEX WORKFLOW: action_set_pendiente_modif_comercial sobre ids %s", self.ids)
        self._set_estado("pendiente_modif_comercial")
        return True

    def action_set_preproduccion(self):
        """Enviar el portón a PRE-PRODUCCIÓN (todavía no está en producción)."""
        _logger.info("DFLEX WORKFLOW: action_set_preproduccion sobre ids %s", self.ids)
        self._set_estado("preproduccion")
        return True

    def action_set_produccion(self):
        """Enviar el portón a PRODUCCIÓN."""
        _logger.info("DFLEX WORKFLOW: action_set_produccion sobre ids %s", self.ids)
        self._set_estado("produccion")
        return True

    # ------------------------------------------------------------------
    # Aprobaciones
    # ------------------------------------------------------------------
    def action_aprobar_comercial(self):
        for rec in self:
            rec.x_aprob_comercial = True
        return True

    def action_rechazar_comercial(self):
        for rec in self:
            rec.x_aprob_comercial = False
        return True

    def action_aprobar_planificacion(self):
        for rec in self:
            rec.x_aprob_planificacion = True
        return True

    def action_rechazar_planificacion(self):
        for rec in self:
            rec.x_aprob_planificacion = False
        return True

    def action_aprobar_administracion(self):
        for rec in self:
            rec.x_aprob_administracion = True
        return True

    def action_rechazar_administracion(self):
        for rec in self:
            rec.x_aprob_administracion = False
        return True
