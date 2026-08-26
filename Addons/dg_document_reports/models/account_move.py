# -*- coding: utf-8 -*-
import base64
import logging
from urllib.parse import quote

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # El campo l10n_ar_afip_qr_code guarda una URL completa de AFIP/ARCA
    # (con su propio "?p=..." adentro). Antes armabamos un
    # <img src="/report/barcode/?..."> que obliga al motor que genera el
    # PDF a salir a buscar esa imagen por HTTP durante la conversion.
    # En este entorno esa peticion interna no llega a buen puerto y el
    # QR no aparece en el PDF final (aunque en el navegador se ve bien).
    # Por eso generamos el QR nosotros mismos en Python y lo embebemos
    # como imagen directa, igual que ya se hace con el logo, sin
    # depender de ninguna peticion de red durante la conversion a PDF.
    dg_qr_barcode_url = fields.Char(
        string="URL del QR (Factura DG)",
        compute="_compute_dg_qr_barcode_url",
    )

    @api.depends("l10n_ar_afip_qr_code")
    def _compute_dg_qr_barcode_url(self):
        report_model = self.env["ir.actions.report"]
        for move in self:
            value = move.l10n_ar_afip_qr_code
            if not value:
                move.dg_qr_barcode_url = False
                continue
            try:
                barcode = report_model.barcode("QR", value, width=150, height=150)
                move.dg_qr_barcode_url = "data:image/png;base64,%s" % (
                    base64.b64encode(barcode).decode()
                )
            except Exception:
                _logger.exception(
                    "dg_document_reports: fallo al generar el QR embebido "
                    "para la factura %s, se usa la URL como respaldo",
                    move.name,
                )
                # Si algo falla al generarlo nosotros, dejamos la URL vieja
                # (por HTTP) como respaldo, para no perder el QR por completo.
                move.dg_qr_barcode_url = (
                    "/report/barcode/?barcode_type=QR&value=%s&width=150&height=150"
                    % quote(value, safe="")
                )
