# -*- coding: utf-8 -*-
import base64
import csv
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PortonImportWizard(models.TransientModel):
    _name = "x_dflex.porton.import.wizard"
    _description = "Importar portones desde CSV"

    file = fields.Binary(string="Archivo CSV", required=True)
    filename = fields.Char(string="Nombre de archivo")
    update_if_exists = fields.Boolean(
        string="Actualizar si existe",
        help="Si hay un portón con el mismo 'name' (x_name), actualiza sus datos en lugar de crear otro."
    )
    delimiter = fields.Char(string="Separador", default=",")
    encoding = fields.Selection(
        [
            ("utf-8-sig", "UTF-8 (con BOM)"),
            ("utf-8", "UTF-8"),
            ("latin1", "Latin-1"),
        ],
        string="Encoding",
        default="utf-8-sig",
    )

    def _map_row_to_vals(self, row):
        def pick(*keys):
            for k in keys:
                if k in row and row[k] not in (None, "", "NULL", "null"):
                    return row[k]
            return False

        return {
            "x_name": pick("name", "NAME", "Name"),
            "x_nombre_del_cliente": pick("Cliente", "CLIENTE"),
            "x_nota_de_Venta": pick("Nota de Venta", "Nota de venta", "NOTA DE VENTA"),
            "x_distribuidor": pick("DISTRIBUIDOR", "Distribuidor"),
            "x_direccion_del_cliente": pick("DIRECCION CLIENTE", "Dirección Cliente", "Direccion Cliente"),
        }

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Subí un archivo CSV.'))

        try:
            text = base64.b64decode(self.file).decode(self.encoding or 'utf-8-sig', errors='ignore')
        except Exception as e:
            raise UserError(_('No pude leer el archivo: %s') % (e,))

        reader = csv.DictReader(io.StringIO(text), delimiter=(self.delimiter or ','))
        if not reader.fieldnames:
            raise UserError(_('El CSV no tiene encabezados.'))

        Porton = self.env['x_dflex.porton'].sudo()
        created, updated, missing = 0, 0, 0

        for row in reader:
            vals = self._map_row_to_vals(row)
            key = vals.get('x_name')
            if not key:
                missing += 1
                continue
            existing = Porton.search([('x_name', '=', key)], limit=1)
            if existing:
                if self.update_if_exists:
                    existing.write({k: v for k, v in vals.items() if v not in (False, None, '')})
                    updated += 1
                continue
            Porton.create(vals)
            created += 1

        msg = _('Importación finalizada. Creados: %(c)s, Actualizados: %(u)s, Filas sin "name": %(m)s') % {
            'c': created, 'u': updated, 'm': missing,
        }
        # Notificación visible arriba a la derecha
        self.env.user.notify_info(message=msg, title=_('Importador de Portones'))
        # Seguir en la misma pantalla del importador
        return {'type': 'ir.actions.act_window_close'}
