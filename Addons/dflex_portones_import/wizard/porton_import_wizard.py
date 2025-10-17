# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _norm(s):
    if not s:
        return ""
    s = str(s).strip()
    repl = {
        "Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ü":"U","Ñ":"N",
        "Ã¡":"a","Ã©":"e","Ã­":"i","Ã³":"o","Ãº":"u","Ã±":"n","Â°":"o",
        "â€¦":"", "…":""
    }
    for k,v in repl.items():
        s = s.replace(k, v)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)

def _to_int(v):
    try:
        if v in (None, ""):
            return False
        return int(float(str(v).replace(",", ".").strip()))
    except Exception:
        return False

def _to_date(v):
    if not v:
        return False
    s = str(v).strip()
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return False

CSV_TO_FIELD = {
    "name": "x_name",
    "nota de venta": "x_nota_de_venta",
    "cliente": "x_nombre_del_cliente",
    "direccion cliente": "x_direccion_del_cliente",
    "distribuidor": "x_distribuidor",
    "estado": "x_estado",
    "partida": "x_partida",

    "fecha de pedido": "x_fecha_de_pedido",
    "fecha de entrega": "x_fecha_de_entrega",
    "fecha entrega estimada": "x_fecha_de_entrega_estimada",
    "fecha inicio produccion": "x_fecha_de_inicio_produccion",

    "dias restantes": "x_dias_restantes",
    "dias transcurrido": "x_dias_transcurridos",
    "dintel ancho": "x_dintel_ancho",
    "hueco chico": "x_hueco_chico",
    "hueco grande": "x_hueco_grande",
    "brazos": "x_largo_brazo",
    "pierna altura": "x_piernas_altura",
    "parantes n pieza": "x_parantes_cantidad",
    "parantes cantidad": "x_parantes_internos_cantidad",

    "rev fabricante": "x_revestimiento_fabricante",
    "rev tipo": "x_revestimiento_tipo",
    "color de simil aluminio": "x_color_del_revestimiento",
    "color de sistema": "x_color_sistema",
    "liston": "x_listones",
    "lucera": "x_lucera",
    "puerta condicion": "x_puerta_condicion",
    "puerta posicion": "x_puerta_posicion",
    "puerta descripcion": "x_puerta_descripcion",
    "condicion": "x_motor_condicion",
    "motor ubicacion": "x_motor_posicion",
    "pasador condicion": "x_pasador",
    "armado puerta": "x_armado",
    "instalador": "x_instalacion",
    "empotra duras": "x_instalacion_empotraduras",
    "empotraduras posicion": "x_empotraduras_posicion",
    "parantes descripcion": "x_parantes_descripcion",
    "parantes distribucion": "x_parantes_distribucion",
    "pierna tipo": "x_piernas_tipo",
    "espesor revest": "x_revestimiento_espesor",
    "dintel tipo": "x_dintel_tipo",
    "rebaje": "x_rebaje",
    "rebaje descuento": "x_rebaje_descuento",
    "rebaje altura": "x_rebaje_altura",
    "rebaje lateral e inferior": "x_rebaje_lateral_inferior",
    "descuento rebaje lateral e inferior": "x_rebaje_lateral_inferior_descuento",
}

CSV_ALIASES = {
    "motor ubicaci n": "motor ubicacion",
    "parantes n pieza": "parantes n pieza",
    "dintel tipo": "dintel tipo",
}

FALLBACK_FIELD = {
    "x_fecha_de_entrega_estimada": "x_fecha_entrega_estimada",
}

TYPE_CONVERTER = {
    "integer": _to_int,
    "float": _to_int,
    "date": _to_date,
}

class PortonImportWizard(models.TransientModel):
    _name = "x_dflex.porton.import.wizard"
    _description = "Importar portones desde CSV"

    file = fields.Binary(string="Archivo CSV", required=True)
    filename = fields.Char(string="Nombre de archivo")
    update_if_exists = fields.Boolean(
        string="Actualizar si existe",
        help="Si existe un portón con el mismo 'x_nota_de_venta' o 'x_name', se actualiza."
    )

    def _model_fields_and_types(self):
        fields_get = self.env["x_dflex.porton"].fields_get()
        return {k: v.get("type") for k, v in fields_get.items()}

    def _convert_auto(self, field_name, value, types_map):
        if value in (None, ""):
            return False
        ftype = types_map.get(field_name)
        conv = TYPE_CONVERTER.get(ftype)
        if conv:
            return conv(value)
        return value

    def _find_existing(self, Model, vals):
        dom = []
        if vals.get("x_nota_de_venta"):
            dom = [("x_nota_de_venta","=", vals["x_nota_de_venta"])]
        elif vals.get("x_name"):
            dom = [("x_name","=", vals["x_name"])]
        return Model.search(dom, limit=1) if dom else Model.browse()

    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Cargá un CSV."))

        try:
            content = base64.b64decode(self.file)
            text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise UserError(_("No se pudo leer el CSV: %s") % e)

        reader = csv.DictReader(io.StringIO(text), delimiter=",")
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        norm_to_field = {}
        for raw in reader.fieldnames:
            nh = _norm(raw)
            nh = CSV_ALIASES.get(nh, nh)
            if nh in CSV_TO_FIELD:
                norm_to_field[nh] = CSV_TO_FIELD[nh]

        Model = self.env["x_dflex.porton"]
        field_types = self._model_fields_and_types()
        field_set = set(field_types.keys())

        created = updated = missing_key = 0
        for idx, row in enumerate(reader, start=2):
            vals = {}
            for raw_h, raw_v in row.items():
                nh = _norm(raw_h)
                nh = CSV_ALIASES.get(nh, nh)
                target = norm_to_field.get(nh)
                if not target:
                    continue
                if target not in field_set and target in FALLBACK_FIELD and FALLBACK_FIELD[target] in field_set:
                    target = FALLBACK_FIELD[target]
                if target not in field_set:
                    continue
                vals[target] = self._convert_auto(target, raw_v, field_types)

            if not vals:
                continue

            if "x_name" not in vals and row.get("name"):
                vals["x_name"] = row["name"]

            existing = self._find_existing(Model, vals)
            if not vals.get("x_name"):
                missing_key += 1
                continue

            if existing and self.update_if_exists:
                existing.write(vals)
                updated += 1
            elif existing:
                vals["x_name"] = f"{vals['x_name']} (imp {idx})"
                Model.create(vals); created += 1
            else:
                Model.create(vals); created += 1

        msg = _("Importación finalizada. Creados: %(c)s, Actualizados: %(u)s, Filas sin 'name': %(m)s") % {
            "c": created, "u": updated, "m": missing_key
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Importación de portones"), "message": msg, "sticky": False},
        }
