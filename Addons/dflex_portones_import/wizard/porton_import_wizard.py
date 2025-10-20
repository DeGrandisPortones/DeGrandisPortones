# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _norm(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    # Normalizar acentos y caracteres raros de CSV exportado
    repl = {
        "Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ü":"U","Ñ":"N",
        "á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n",
        "Â°":"o", "…":"", "â€¦":"",
    }
    for k,v in repl.items():
        s = s.replace(k,v)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s

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

# 1) CSV header (normalizado) -> clave canónica
CSV_TO_CANONICAL = {
    "name": "name",
    "nota de venta": "nv",
    "cliente": "cliente",
    "direccion cliente": "direccion",
    "distribuidor": "distribuidor",
    "estado": "estado",
    "partida": "partida",

    "fecha de pedido": "fecha_pedido",
    "fecha de entrega": "fecha_entrega",
    "fecha entrega estimada": "fecha_entrega_estimada",
    "fecha inicio produccion": "fecha_inicio_prod",

    "dias restantes": "dias_restantes",
    "dias transcurrido": "dias_transcurridos",

    "color de simil aluminio": "color_revest",
    "rev fabricante": "revest_fabricante",
    "rev tipo": "revest_tipo",
    "color de sistema": "color_sistema",

    "liston": "listones",
    "lucera": "lucera",
    "puerta condicion": "puerta_condicion",
    "puerta posicion": "puerta_posicion",
    "puerta descripcion": "puerta_descripcion",
    "armado puerta": "armado_puerta",
    "puerta": "puerta",
    "pasador condicion": "pasador",

    "instalador": "instalador",
    "empotra duras": "empotraduras",
    "empotraduras posicion": "empotraduras_posicion",

    "parantes n pieza": "parantes_pieza",
    "parantes cantidad": "parantes_cant_int",
    "parantes distribucion": "parantes_distrib",
    "parantes descripcion": "parantes_desc",

    "pierna tipo": "piernas_tipo",
    "pierna altura": "piernas_altura",

    "dintel tipo": "dintel_tipo",
    "dintel ancho": "dintel_ancho",

    "motor ubicacion": "motor_posicion",
    "condicion": "motor_condicion",

    "hueco chico": "hueco_chico",
    "hueco grande": "hueco_grande",
    "brazos": "brazos",

    "espesor revest": "revest_espesor",

    "rebaje": "rebaje",
    "rebaje descuento": "rebaje_descuento",
    "rebaje altura": "rebaje_altura",
    "rebaje lateral e inferior": "rebaje_lat_inf",
    "descuento rebaje lateral e inferior": "rebaje_lat_inf_desc",
}

# 2) clave canónica -> lista de nombres de campo candidatos (el primero que exista se usa)
CANONICAL_TO_FIELDS = {
    "name": ["x_name"],
    "nv": ["x_nota_de_venta", "x_nv", "x_nro_nota_venta"],
    "cliente": ["x_nombre_del_cliente", "x_cliente"],
    "direccion": ["x_direccion_del_cliente", "x_direccion"],
    "distribuidor": ["x_distribuidor"],
    "estado": ["x_estado"],
    "partida": ["x_partida"],

    "fecha_pedido": ["x_fecha_de_pedido","x_fecha_pedido"],
    "fecha_entrega": ["x_fecha_de_entrega","x_fecha_entrega"],
    "fecha_entrega_estimada": ["x_fecha_de_entrega_estimada","x_fecha_entrega_estimada"],
    "fecha_inicio_prod": ["x_fecha_de_inicio_produccion","x_fecha_inicio_produccion"],

    "dias_restantes": ["x_dias_restantes"],
    "dias_transcurridos": ["x_dias_transcurridos"],

    "color_revest": ["x_color_del_revestimiento"],
    "revest_fabricante": ["x_revestimiento_fabricante"],
    "revest_tipo": ["x_revestimiento_tipo"],
    "color_sistema": ["x_color_sistema"],

    "listones": ["x_listones"],
    "lucera": ["x_lucera"],
    "puerta_condicion": ["x_puerta_condicion","x_puerta"],
    "puerta_posicion": ["x_puerta_posicion","x_puerta_position","x_puerta_pos"],
    "puerta_descripcion": ["x_puerta_descripcion","x_puerta_desc"],
    "armado_puerta": ["x_armado","x_armado_puerta"],
    "puerta": ["x_puerta","x_puerta_condicion"],  # por si lo tenés así

    "pasador": ["x_pasador","x_pasador_condicion"],

    "instalador": ["x_instalacion"],
    "empotraduras": ["x_instalacion_empotraduras"],
    "empotraduras_posicion": ["x_empotraduras_posicion","x_empotradura_posicion"],

    "parantes_pieza": ["x_parantes_cantidad"],
    "parantes_cant_int": ["x_parantes_internos_cantidad"],
    "parantes_distrib": ["x_parantes_distribucion"],
    "parantes_desc": ["x_parantes_descripcion"],

    "piernas_tipo": ["x_piernas_tipo"],
    "piernas_altura": ["x_piernas_altura"],

    "dintel_tipo": ["x_dintel_tipo"],
    "dintel_ancho": ["x_dintel_ancho"],

    "motor_posicion": ["x_motor_posicion","x_motor_ubicacion"],
    "motor_condicion": ["x_motor_condicion"],

    "hueco_chico": ["x_hueco_chico"],
    "hueco_grande": ["x_hueco_grande"],
    "brazos": ["x_largo_brazo"],

    "revest_espesor": ["x_revestimiento_espesor"],

    "rebaje": ["x_rebaje"],
    "rebaje_descuento": ["x_rebaje_descuento"],
    "rebaje_altura": ["x_rebaje_altura"],
    "rebaje_lat_inf": ["x_rebaje_lateral_inferior"],
    "rebaje_lat_inf_desc": ["x_rebaje_lateral_inferior_descuento"],
}

TYPE_CONVERTER = {
    "date": _to_date,
    "integer": _to_int,
    "float": _to_int,
    # char/text/selection: sin conversión
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

    def _pick_existing_field(self, canonical_key, field_types):
        for fname in CANONICAL_TO_FIELDS.get(canonical_key, []):
            if fname in field_types:
                return fname
        return None

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

        # Construir mapa de encabezado -> clave canónica
        hdr_to_canon = {}
        for h in reader.fieldnames:
            nh = _norm(h)
            # alias para errores de tipeo comunes
            if nh == "destribucion": nh = "distribucion"
            hdr_to_canon[nh] = CSV_TO_CANONICAL.get(nh)

        Model = self.env["x_dflex.porton"]
        field_types = self._model_fields_and_types()

        created = updated = missing_key = 0
        for idx, row in enumerate(reader, start=2):
            vals = {}
            for raw_h, raw_v in row.items():
                canon = hdr_to_canon.get(_norm(raw_h))
                if not canon:
                    continue
                target = self._pick_existing_field(canon, field_types)
                if not target:
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
                existing.write(vals); updated += 1
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
