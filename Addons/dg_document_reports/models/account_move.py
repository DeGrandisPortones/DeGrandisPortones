# -*- coding: utf-8 -*-
from urllib.parse import quote

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # El campo l10n_ar_afip_qr_code guarda una URL completa de AFIP/ARCA
    # (con su propio "?p=..." adentro). Si se pega tal cual dentro de la
    # URL de /report/barcode/, queda una URL con dos signos "?", y el
    # motor que arma el PDF (wkhtmltopdf) la corta ahi y el QR no sale.
    # Por eso armamos aca la URL ya con el valor correctamente escapado.
    dg_qr_barcode_url = fields.Char(
        string="URL del QR (Factura DG)",
        compute="_compute_dg_qr_barcode_url",
    )

    @api.depends("l10n_ar_afip_qr_code")
    def _compute_dg_qr_barcode_url(self):
        for move in self:
            if move.l10n_ar_afip_qr_code:
                move.dg_qr_barcode_url = (
                    "/report/barcode/?barcode_type=QR&value=%s&width=150&height=150"
                    % quote(move.l10n_ar_afip_qr_code, safe="")
                )
            else:
                move.dg_qr_barcode_url = False
