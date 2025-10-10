from odoo import api, fields, models
from odoo.exceptions import UserError
import re, unicodedata

def _norm(s):
    return (str(s) if s is not None else '').strip()

def _lower(s):
    return _norm(s).lower()

def _slug(label):
    s = _norm(label)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()
    if not s:
        s = 'col'
    if s[0].isdigit():
        s = 'c_' + s
    return s[:50]

class DflexBulkFieldsWizard(models.TransientModel):
    _name = 'dflex.bulk.fields.wizard'
    _description = 'Crear campos en dflex.porton desde encabezados CSV'

    header_line = fields.Text(
        string="Encabezados CSV (una línea)",
        help="Pegá aquí la PRIMERA FILA del CSV (separada por coma , o punto y coma ;)."
    )
    delimiter = fields.Selection(
        [('auto','Auto'), (',', 'Coma (,)'), (';', 'Punto y coma (;)')],
        string="Separador",
        default='auto',
        required=True,
    )

    def _split_headers(self, text, delimiter):
        text = _norm(text)
        if not text:
            raise UserError("Pegá una línea de encabezados.")
        if delimiter == 'auto':
            if text.count(';') > text.count(','):
                delimiter = ';'
            else:
                delimiter = ','
        parts = [h.strip() for h in text.split(delimiter)]
        return parts

    def _should_skip(self, label):
        l = _lower(label)
        if not l:
            return True
        if l == 'name':
            return True
        if re.match(r'^\s*columna\\b', l):
            return True
        return False

    def action_create_fields(self):
        self.ensure_one()
        headers = self._split_headers(self.header_line or '', self.delimiter)
        if not headers:
            raise UserError("No se detectaron encabezados.")

        model = self.env['ir.model'].sudo().search([('model', '=', 'dflex.porton')], limit=1)
        if not model:
            raise UserError("No existe el modelo dflex.porton. Asegurate de tener instalado este módulo CORE.")

        Fields = self.env['ir.model.fields'].sudo()
        created, skipped = [], []
        seen_tech = set()

        for h in headers:
            if self._should_skip(h):
                skipped.append(h)
                continue
            tech = ('x_%s' % _slug(h))[:63]
            base = tech
            i = 1
            while tech in seen_tech or Fields.search_count([('model_id','=',model.id),('name','=',tech)]):
                i += 1
                tech = (base[:60] + '_' + str(i))[:63]
            seen_tech.add(tech)

            field = Fields.search([('model_id','=',model.id), ('name','=',tech)], limit=1)
            if not field:
                Fields.create({
                    'name': tech,
                    'model_id': model.id,
                    'ttype': 'char',
                    'field_description': _norm(h),
                    'store': True,
                })
                created.append(tech)
            else:
                skipped.append(h)

        msg = "Campos creados: %s\nOmitidos: %s" % (
            (', '.join(created) or '—'),
            (', '.join(skipped) or '—')
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Resultado', 'message': msg, 'sticky': False},
        }