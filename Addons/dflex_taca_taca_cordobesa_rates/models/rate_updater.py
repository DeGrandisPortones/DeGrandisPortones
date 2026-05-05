# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DflexTacaTacaCordobesaRateUpdater(models.AbstractModel):
    _name = "dflex.taca.taca.cordobesa.rate.updater"
    _description = "Actualizador tasas Cordobesa Taca Taca"

    # Valores nuevos solicitados.
    #
    # Nota: 2 cuotas no venía en el listado de porcentajes informado. Se agrega
    # con 0% de recargo para que aparezca como alternativa sin interés/recargo.
    TARGET_RATES = {
        2: 0.0,
        4: 10.0,
        6: 15.0,
        10: 20.0,
        12: 24.0,
        14: 28.0,
        18: 33.0,
    }

    INSTALLMENT_FIELDS = (
        "installments",
        "installment",
        "installment_count",
        "number_of_installments",
        "quantity",
        "qty",
        "cuotas",
        "quota",
        "quota_count",
        "term",
        "months",
    )

    RATE_FIELDS = (
        "surcharge_percentage",
        "recargo_percentage",
        "percentage",
        "rate",
        "interest_rate",
        "interest_percentage",
        "fee_percentage",
        "financing_percentage",
        "extra_percentage",
        "surcharge",
        "recargo",
    )

    def _safe_display_name(self, record):
        try:
            return record.display_name or ""
        except Exception:
            return ""

    def _record_text(self, record):
        parts = [self._safe_display_name(record)]
        for field_name in ("name", "description", "display_name"):
            if field_name in record._fields:
                try:
                    value = record[field_name]
                    if value:
                        parts.append(str(value))
                except Exception:
                    pass
        return " ".join(parts)

    def _looks_like_cordobesa_record(self, record):
        text = self._record_text(record).lower()
        return (
            "cordobesa" in text
            or "tarjeta cordobesa" in text
            or "taca taca" in text
            or "taca" in text
        )

    def _get_installment_field(self, record):
        for field_name in self.INSTALLMENT_FIELDS:
            field = record._fields.get(field_name)
            if not field:
                continue
            if field.type not in ("integer", "float", "monetary", "selection", "char"):
                continue
            try:
                value = record[field_name]
            except Exception:
                continue
            if isinstance(value, models.BaseModel):
                continue
            try:
                value_int = int(value)
            except Exception:
                continue
            if value_int in self.TARGET_RATES:
                return field_name
        return False

    def _get_installments(self, record):
        field_name = self._get_installment_field(record)
        if field_name:
            try:
                return int(record[field_name])
            except Exception:
                pass

        text = self._record_text(record).lower()
        for match in re.finditer(r"(\d+)\s*(?:cuota|cuotas|c\.|x)", text):
            value = int(match.group(1))
            if value in self.TARGET_RATES:
                return value

        for value in self.TARGET_RATES:
            if re.search(rf"(^|[^\d]){value}([^\d]|$)", text):
                return value

        return False

    def _get_rate_field(self, record):
        for field_name in self.RATE_FIELDS:
            field = record._fields.get(field_name)
            if not field:
                continue
            if field.type not in ("float", "monetary", "integer"):
                continue
            return field_name

        for field_name, field in record._fields.items():
            if field.type not in ("float", "monetary", "integer"):
                continue
            lowered = field_name.lower()
            if any(token in lowered for token in ("percent", "percentage", "rate", "interest", "recargo", "surcharge")):
                return field_name

        return False

    def _get_name_default(self, template, installments):
        text = self._record_text(template)
        replacement = "%s cuotas" % installments

        if text:
            new_text = re.sub(r"\d+\s*(cuota|cuotas|c\.|x)", replacement, text, count=1, flags=re.I)
            if new_text != text:
                return new_text

        return "Tarjeta Cordobesa - %s cuotas" % installments

    @api.model
    def _get_original_taca_records(self):
        data_records = self.env["ir.model.data"].sudo().search([
            ("module", "=", "dflex_sale_financing_taca_taca"),
        ])

        records_by_model = {}
        for data in data_records:
            if not data.model or not data.res_id:
                continue
            if data.model not in self.env:
                continue
            record = self.env[data.model].sudo().browse(data.res_id).exists()
            if not record:
                continue
            records_by_model.setdefault(data.model, self.env[data.model].sudo().browse())
            records_by_model[data.model] |= record

        return records_by_model

    def _get_best_template(self, model_records, target_installments):
        candidates = []
        for record in model_records:
            installments = self._get_installments(record)
            rate_field = self._get_rate_field(record)
            if not installments or not rate_field:
                continue
            if not self._looks_like_cordobesa_record(record):
                # Igual puede servir si el XML del módulo sólo tenía "4 cuotas", etc.
                pass
            candidates.append((abs(installments - target_installments), record))

        if not candidates:
            return False

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def _create_missing_rate_record(self, model_records, installments, rate):
        template = self._get_best_template(model_records, installments)
        if not template:
            return False

        rate_field = self._get_rate_field(template)
        installment_field = self._get_installment_field(template)
        if not rate_field:
            return False

        defaults = {
            rate_field: rate,
        }

        if installment_field:
            field = template._fields[installment_field]
            if field.type in ("integer", "float", "monetary"):
                defaults[installment_field] = installments
            else:
                defaults[installment_field] = str(installments)

        if "name" in template._fields:
            defaults["name"] = self._get_name_default(template, installments)
        if "description" in template._fields:
            defaults["description"] = self._get_name_default(template, installments)

        new_record = template.copy(default=defaults)

        self.env["ir.model.data"].sudo().create({
            "module": "dflex_taca_taca_cordobesa_rates",
            "name": "cordobesa_%s_cuotas" % installments,
            "model": new_record._name,
            "res_id": new_record.id,
            "noupdate": True,
        })

        _logger.info(
            "Taca Taca Cordobesa: creado registro %s/%s para %s cuotas -> %s%%",
            new_record._name,
            new_record.id,
            installments,
            rate,
        )
        return new_record

    @api.model
    def update_cordobesa_rates(self):
        updated = {}
        inspected = []
        records_by_model = self._get_original_taca_records()

        for model_name, records in records_by_model.items():
            for record in records:
                installments = self._get_installments(record)
                if not installments:
                    continue

                if not self._looks_like_cordobesa_record(record):
                    _logger.info(
                        "Actualizando candidato Taca Taca sin etiqueta Cordobesa explícita: %s/%s (%s)",
                        model_name,
                        record.id,
                        self._safe_display_name(record),
                    )

                rate_field = self._get_rate_field(record)
                if not rate_field:
                    inspected.append("%s,%s,%s" % (model_name, record.id, self._safe_display_name(record)))
                    continue

                new_rate = self.TARGET_RATES[installments]
                record.write({rate_field: new_rate})
                updated[installments] = updated.get(installments, 0) + 1

                _logger.info(
                    "Taca Taca Cordobesa: actualizado %s/%s cuota %s -> %s%% en campo %s",
                    model_name,
                    record.id,
                    installments,
                    new_rate,
                    rate_field,
                )

        # Crear cuotas que no existían en el módulo original, por ejemplo 2 y 12.
        missing = sorted(set(self.TARGET_RATES) - set(updated))
        if missing:
            # Elegimos el modelo con mayor cantidad de registros detectados.
            candidate_models = sorted(records_by_model.items(), key=lambda item: len(item[1]), reverse=True)
            for installments in list(missing):
                created = False
                for _model_name, model_records in candidate_models:
                    new_record = self._create_missing_rate_record(
                        model_records,
                        installments,
                        self.TARGET_RATES[installments],
                    )
                    if new_record:
                        updated[installments] = 1
                        created = True
                        break
                if not created:
                    inspected.append("No se pudo crear %s cuotas" % installments)

        missing = sorted(set(self.TARGET_RATES) - set(updated))
        if missing:
            raise UserError(
                "No se pudieron actualizar/crear todas las tasas de Cordobesa/Taca Taca. "
                "Faltan cuotas: %s. Registros inspeccionados sin campo de tasa: %s"
                % (", ".join(str(x) for x in missing), "; ".join(inspected[:10]))
            )

        return True
