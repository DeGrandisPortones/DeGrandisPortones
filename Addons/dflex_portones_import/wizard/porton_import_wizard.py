# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

SKIP_FIELDS = {
    'id','display_name','create_uid','create_date','write_uid','write_date','__last_update'
}

def _to_bool(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    s = {'sí':'si'}.get(s, s)
    return s in {'1','true','t','y','yes','si','s','x','verdadero'}

def _to_int(v):
    try:
        if v in (None, ''):
            return False
        return int(float(str(v).replace(',', '.').strip()))
    except Exception:
        return False

def _to_float(v):
    try:
        if v in (None, ''):
            return False
        return float(str(v).replace(',', '.').strip())
    except Exception:
        return False

def _to_date(v):
    if not v:
        return False
    s = str(v).strip()
    m = re.match(r'^(\d{2,4}[/-]\d{1,2}[/-]\d{1,4})', s)
    if m:
        s_only = m.group(1)
    else:
        s_only = s
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%m/%d/%Y','%Y/%m/%d'):
        try:
            return datetime.strptime(s_only, fmt).date().isoformat()
        except Exception:
            pass
    return False
    s = str(v).strip()
    for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return False

def _to_datetime(v):
    if not v:
        return False
    s = str(v).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%d/%m/%Y %H:%M:%S','%Y-%m-%d %H:%M','%d/%m/%Y %H:%M'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
    d = _to_date(s)
    return f"{d} 00:00:00" if d else False

TYPE_CONVERTER = {
    'boolean': _to_bool,
    'integer': _to_int,
    'float': _to_float,
    'monetary': _to_float,
    'date': _to_date,
    'datetime': _to_datetime,
}

class PortonImportWizard(models.TransientModel):
    _name = 'x_dflex.porton.import.wizard'
    _description = 'Importar portones desde CSV (headers = códigos de campo)'

    file = fields.Binary(string='Archivo CSV', required=True)
    filename = fields.Char(string='Nombre de archivo')
    update_if_exists = fields.Boolean(
        string='Actualizar si existe',
        help="Si existe un portón con el mismo 'x_nota_de_venta' o 'x_name', se actualiza."
    )

    def _fields_types(self):
        fields_get = self.env['x_dflex.porton'].fields_get()
        return {k: v.get('type') for k, v in fields_get.items()}

    def _convert(self, fname, value, types_map):
        if value in (None, ''):
            return False
        ftype = types_map.get(fname)
        conv = TYPE_CONVERTER.get(ftype)
        if conv:
            return conv(value)
        return value

    def _find_existing(self, Model, vals):
        if vals.get('x_nota_de_venta'):
            return Model.search([('x_nota_de_venta','=', vals['x_nota_de_venta'])], limit=1)
        if vals.get('x_name'):
            return Model.search([('x_name','=', vals['x_name'])], limit=1)
        return Model.browse()

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Cargá un CSV.'))

        try:
            content = base64.b64decode(self.file)
            text = content.decode('utf-8-sig', errors='ignore')
        except Exception as e:
            raise UserError(_('No se pudo leer el CSV: %s') % e)

        reader = csv.DictReader(io.StringIO(text), delimiter=',')
        if not reader.fieldnames:
            raise UserError(_('El CSV no tiene encabezados.'))

        Model = self.env['x_dflex.porton']
        types_map = self._fields_types()
        allowed = set(types_map.keys()) - SKIP_FIELDS

        created = updated = skipped_no_key = 0
        for idx, row in enumerate(reader, start=2):
            vals = {}
            for key, val in row.items():
                key = (key or '').strip()
                if not key or key not in allowed:
                    continue
                ftype = types_map.get(key)
                if ftype in {'many2one','one2many','many2many','reference'}:
                    continue
                vals[key] = self._convert(key, val, types_map)

            if 'x_name' not in vals and 'name' in row and 'x_name' in allowed and row.get('name'):
                vals['x_name'] = row['name']

            if not vals:
                continue

            existing = self._find_existing(Model, vals)
            if not vals.get('x_name'):
                skipped_no_key += 1
                continue

            if existing and self.update_if_exists:
                existing.write(vals); updated += 1
            elif existing:
                vals['x_name'] = f"{vals['x_name']} (imp {idx})"
                Model.create(vals); created += 1
            else:
                Model.create(vals); created += 1

        msg = _('Importación finalizada. Creados: %(c)s, Actualizados: %(u)s, Filas sin x_name: %(m)s') % {
            'c': created, 'u': updated, 'm': skipped_no_key
        }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Importación de portones'), 'message': msg, 'sticky': False},
        }
