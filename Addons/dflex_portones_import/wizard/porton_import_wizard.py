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
        """
        row: dict de una fila del CSV.
        Devuelve el dict de valores para crear/escribir en x_dflex.porton.
        """
        def pick(*keys):
            for k in keys:
                if k in row and row[k] not in (None, "", "NULL", "null"):
                    return row[k]
            return False

        return {
            # Mapeo CSV -> Modelo
            "x_name": pick("name", "NAME", "Name"),
            "x_nombre_del_cliente": pick("Cliente", "CLIENTE"),
            "x_nota_de_Venta": pick("Nota de Venta", "Nota de venta", "NOTA DE VENTA"),
            "x_distribuidor": pick("DISTRIBUIDOR", "Distribuidor"),
            "x_direccion_del_cliente": pick("DIRECCION CLIENTE", "Dirección Cliente", "Direccion Cliente"),
        }

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Subí un archivo CSV."))

        # Decodificar el binario
        try:
            content = base64.b64decode(self.file)
        except Exception:
            raise UserError(_("No pude decodificar el archivo cargado."))

        # Leer CSV con el encoding seleccionado
        try:
            text = content.decode(self.encoding or "utf-8-sig", errors="ignore")
        except Exception as e:
            raise UserError(_("Error decodificando el archivo: %s") % (e,))

        # csv.DictReader necesita un stream de texto
        f = io.StringIO(text)
        try:
            reader = csv.DictReader(f, delimiter=(self.delimiter or ","))
        except Exception as e:
            raise UserError(_("No pude leer el CSV: %s") % (e,))

        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        Porton = self.env["x_dflex.porton"].sudo()
        created = 0
        updated = 0
        missing_key = 0

        for row in reader:
            vals = self._map_row_to_vals(row)
            key = vals.get("x_name")  # usamos x_name como identificador único

            if not key:
                missing_key += 1
                continue

            # Buscar existente por x_name
            existing = Porton.search([("x_name", "=", key)], limit=1)
            if existing:
                if self.update_if_exists:
                    existing.write({k: v for k, v in vals.items() if v not in (False, None, "")})
                    updated += 1
                continue

            Porton.create(vals)
            created += 1

        msg = _("Importación finalizada. Creados: %(c)s, Actualizados: %(u)s, Filas sin 'name': %(m)s") % {
            "c": created,
            "u": updated,
            "m": missing_key,
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Importación de portones"), "message": msg, "sticky": False},
        }
