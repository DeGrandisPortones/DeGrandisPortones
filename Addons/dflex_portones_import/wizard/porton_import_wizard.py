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
    s = "".join({"Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ü":"U","Ñ":"N"}.get(c, c) for c in s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)

def _to_bool(v):
    if v is None:
        return False
    s = str(v).strip().lower()
    s = {"sí":"si"}.get(s, s)
    return s in {"1","true","t","y","yes","si","s","x","verdadero"}

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

# Encabezado CSV (normalizado) -> campo tecnico en x_dflex.porton
CSV_TO_FIELD = {
    # Identificación
    "name": "x_name",
    "nota de venta": "x_nota_de_venta",
    "cliente": "x_nombre_del_cliente",
    "direccion cliente": "x_direccion_del_cliente",
    "distribuidor": "x_distribuidor",
    "estado": "x_estado",
    "partida": "x_partida",

    # Fechas
    "fecha de pedido": "x_fecha_de_pedido",
    "fecha de entrega": "x_fecha_de_entrega",
    "fecha entrega estimada": "x_fecha_de_entrega_estimada",
    "fecha de inicio de produccion": "x_fecha_de_inicio_produccion",
    "fecha de inicio produccion": "x_fecha_de_inicio_produccion",

    # Números
    "dias transcurrido": "x_dias_transcurridos",
    "dias transcurridos": "x_dias_transcurridos",
    "dias restantes": "x_dias_restantes",
    "dintel ancho": "x_dintel_ancho",
    "hueco chico": "x_hueco_chico",
    "hueco grande": "x_hueco_grande",
    "pierna altura": "x_piernas_altura",
    "brazos": "x_largo_brazo",
    "parantes cantidad": "x_parantes_cantidad",
    "parantes internos cantidad": "x_parantes_internos_cantidad",

    # Textos / selecciones
    "rev fabricante": "x_color_del_revestimiento",
    "rev tipo": "x_color_sistema",
    "dintel tipo": "x_dintel_tipo",
    "listones": "x_listones",
    "instalador": "x_instalacion",
    "par distribucion": "x_parantes_distribucion",
    "par descripcion": "x_parantes_descripcion",
    "pierna tipo": "x_piernas_tipo",
    "observaciones": "x_observaciones",

    # Booleanos / otros
    "lucera": "x_lucera",
    "puerta": "x_puerta",
    "empotraduras": "x_instalacion_empotraduras",
    "pasador condicion": "x_pasador_condicion",

    # Motor
    "motor condicion": "x_motor_condicion",
    "motor posicion": "x_motor_posicion",
    "motor doble": "x_motor_posicion",  # alias
}

TYPE_CONVERTER = {
    "boolean": _to_bool,
    "integer": _to_int,
    "float": _to_int,  # si definiste float, se castea a int sin decimales
    "date": _to_date,
    # "char"/"text"/"selection": por defecto -> string
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

    # Helpers
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
        return value  # char/text/selection/etc.

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

        # Leer CSV (UTF-8, delimitador coma)
        try:
            content = base64.b64decode(self.file)
            text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise UserError(_("No se pudo leer el CSV: %s") % e)

        reader = csv.DictReader(io.StringIO(text), delimiter=",")
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        # Normalizar encabezados
        norm_map = {}
        for h in reader.fieldnames:
            nh = _norm(h)
            if nh in CSV_TO_FIELD:
                norm_map[nh] = CSV_TO_FIELD[nh]

        Model = self.env["x_dflex.porton"]
        field_types = self._model_fields_and_types()

        created = updated = missing_key = 0
        for idx, row in enumerate(reader, start=2):
            vals = {}
            for raw_h, raw_v in row.items():
                target = norm_map.get(_norm(raw_h))
                if not target:
                    continue
                # no escribir si el campo no existe en el modelo
                if target not in field_types:
                    continue
                vals[target] = self._convert_auto(target, raw_v, field_types)

            if not vals:
                continue

            # Asegurar x_name si viene "name" sin mapear
            if "x_name" not in vals and row.get("name"):
                vals["x_name"] = row["name"]

            # Crear/Actualizar
            existing = self._find_existing(Model, vals)
            if not vals.get("x_name"):
                missing_key += 1
                continue

            if existing and self.update_if_exists:
                existing.write(vals)
                updated += 1
            elif existing:
                # si existe y no se pidió actualizar, crea duplicado con sufijo
                vals["x_name"] = f"{vals['x_name']} (imp {idx})"
                Model.create(vals)
                created += 1
            else:
                Model.create(vals)
                created += 1

        msg = _("Importación finalizada. Creados: %(c)s, Actualizados: %(u)s, Filas sin 'name': %(m)s") % {
            "c": created, "u": updated, "m": missing_key
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Importación de portones"), "message": msg, "sticky": False},
        }
