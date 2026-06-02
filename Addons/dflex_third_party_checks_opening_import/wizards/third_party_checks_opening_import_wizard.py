# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from decimal import Decimal, InvalidOperation

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DflexThirdPartyChecksOpeningImportWizard(models.TransientModel):
    _name = "dflex.third.party.checks.opening.import.wizard"
    _description = "Importar cheques de terceros en cartera inicial"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario Cheques de terceros",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Método de pago",
        required=True,
        help="Debe ser el método de recepción de cheques de terceros, normalmente new_third_party_checks.",
    )
    capital_account_id = fields.Many2one(
        "account.account",
        string="Cuenta Capital integrado",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
        help="Cuenta de contrapartida de apertura. Ejemplo: 3.1.1.01.002 Capital integrado.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto de apertura",
        help="Si queda vacío, se usa o crea 'Apertura cheques de terceros'.",
    )
    accounting_date = fields.Date(
        string="Fecha contable",
        required=True,
        default=fields.Date.context_today,
    )
    csv_file = fields.Binary(string="Archivo CSV", required=True)
    csv_filename = fields.Char(string="Nombre archivo")
    dry_run = fields.Boolean(string="Solo simular, no crear nada", default=True)
    post_payments = fields.Boolean(
        string="Publicar pagos de apertura",
        default=False,
        help="Para que queden plenamente en cartera, los pagos deben publicarse. Recomendado: simular primero.",
    )
    result = fields.Text(string="Resultado", readonly=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            account = self._find_account_by_code("3.1.1.01.002", self.company_id)
            if account:
                self.capital_account_id = account

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        for wizard in self:
            wizard.payment_method_line_id = False
            if wizard.journal_id:
                method = wizard._find_third_party_new_method(wizard.journal_id)
                if method:
                    wizard.payment_method_line_id = method

    def _find_account_by_code(self, code, company):
        Account = self.env["account.account"].with_company(company).with_context(allowed_company_ids=[company.id])
        domain = [("code", "=", code)]
        if "company_ids" in Account._fields:
            domain.append(("company_ids", "in", company.id))
        elif "company_id" in Account._fields:
            domain.append(("company_id", "=", company.id))
        return Account.search(domain, limit=1)

    def _find_third_party_new_method(self, journal):
        methods = journal.inbound_payment_method_line_ids.filtered(
            lambda line: (
                line.code == "new_third_party_checks"
                or line.payment_method_id.code == "new_third_party_checks"
                or "third party" in " ".join(
                    part for part in [line.name, line.payment_method_id.name] if part
                ).lower()
                or "tercer" in " ".join(
                    part for part in [line.name, line.payment_method_id.name] if part
                ).lower()
            )
        )
        return methods[:1]

    def _decode_csv(self):
        if not self.csv_file:
            raise UserError(_("Subí un archivo CSV."))
        raw = base64.b64decode(self.csv_file)
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UserError(_("No se pudo leer el CSV. Guardalo como UTF-8 o ANSI/Latin-1."))

    def _iter_csv_rows(self):
        text = self._decode_csv()
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        normalized = {name: self._normalize_header(name) for name in reader.fieldnames}
        required = {"number", "amount", "payment_date"}
        missing = required - set(normalized.values())
        if missing:
            raise UserError(
                _("Faltan columnas obligatorias en el CSV: %s") % ", ".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            data = {}
            for original_name, value in row.items():
                if original_name is None:
                    continue
                key = normalized.get(original_name)
                if key:
                    data[key] = (value or "").strip()
            if not any(data.values()):
                continue
            data["_line_number"] = line_number
            yield data

    def _normalize_header(self, name):
        key = (name or "").strip().lower()
        key = key.replace(" ", "_").replace("-", "_")
        aliases = {
            "nro": "number",
            "numero": "number",
            "número": "number",
            "num": "number",
            "check": "number",
            "cheque": "number",
            "importe": "amount",
            "monto": "amount",
            "fecha": "payment_date",
            "fecha_pago": "payment_date",
            "fecha_de_pago": "payment_date",
            "vencimiento": "payment_date",
            "fecha_vencimiento": "payment_date",
            "fecha_emision": "issue_date",
            "fecha_de_emision": "issue_date",
            "emision": "issue_date",
            "emisión": "issue_date",
            "razon_social": "issuer_name",
            "razón_social": "issuer_name",
            "emisor": "issuer_name",
            "issuer": "issuer_name",
            "cuit": "issuer_vat",
            "cuit_emisor": "issuer_vat",
            "vat": "issuer_vat",
            "nota": "note",
            "observacion": "note",
            "observación": "note",
            "memo": "note",
        }
        return aliases.get(key, key)

    def _parse_amount(self, value, line_number):
        if not value:
            raise UserError(_("Línea %s: falta el importe.") % line_number)
        clean = re.sub(r"[^0-9,\.\-]", "", value)
        if "," in clean and "." in clean:
            # Formato AR: 1.234.567,89
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(",", ".")
        try:
            amount = Decimal(clean)
        except InvalidOperation:
            raise UserError(_("Línea %s: importe inválido: %s") % (line_number, value))
        if amount <= 0:
            raise UserError(_("Línea %s: el importe debe ser mayor a cero.") % line_number)
        return float(amount)

    def _parse_date(self, value, line_number, required=True):
        if not value:
            if required:
                raise UserError(_("Línea %s: falta la fecha.") % line_number)
            return False
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return fields.Date.to_date(fields.Date.from_string(value)) if fmt == "%Y-%m-%d" else self._parse_date_with_format(value, fmt)
            except Exception:
                continue
        raise UserError(_("Línea %s: fecha inválida: %s") % (line_number, value))

    def _parse_date_with_format(self, value, fmt):
        from datetime import datetime
        return datetime.strptime(value, fmt).date()

    def _get_or_create_opening_partner(self):
        if self.partner_id:
            return self.partner_id
        Partner = self.env["res.partner"].with_company(self.company_id).with_context(allowed_company_ids=[self.company_id.id])
        partner = Partner.search([("name", "=", "Apertura cheques de terceros")], limit=1)
        if not partner and not self.dry_run:
            partner = Partner.create({"name": "Apertura cheques de terceros", "company_id": False})
        return partner

    def _validate_configuration(self):
        self.ensure_one()
        company = self.company_id
        if self.journal_id.company_id != company:
            raise UserError(_("El diario no pertenece a la compañía seleccionada."))
        if self.payment_method_line_id not in self.journal_id.inbound_payment_method_line_ids:
            raise UserError(_("El método de pago debe estar en Pagos entrantes del diario seleccionado."))
        method_code = self.payment_method_line_id.code or self.payment_method_line_id.payment_method_id.code
        if method_code != "new_third_party_checks":
            raise UserError(
                _("El método seleccionado no es 'new_third_party_checks'. Seleccioná el método de recepción de nuevos cheques de terceros.")
            )
        if not self.payment_method_line_id.payment_account_id:
            raise UserError(
                _("El método de pago no tiene Cuenta de recibos pendientes. Configurá ahí la cuenta Cheques de Terceros en cartera.")
            )
        if not self.capital_account_id:
            raise UserError(_("Seleccioná la cuenta Capital integrado."))
        if "company_ids" in self.capital_account_id._fields:
            if company not in self.capital_account_id.company_ids:
                raise UserError(_("La cuenta Capital integrado no pertenece a la compañía seleccionada."))
        elif "company_id" in self.capital_account_id._fields:
            if self.capital_account_id.company_id != company:
                raise UserError(_("La cuenta Capital integrado no pertenece a la compañía seleccionada."))
        Payment = self.env["account.payment"]
        if "l10n_latam_new_check_ids" not in Payment._fields:
            raise UserError(_("No está disponible el campo l10n_latam_new_check_ids. Revisá el módulo l10n_latam_check."))
        if "destination_account_id" not in Payment._fields:
            raise UserError(_("No está disponible destination_account_id en account.payment."))

    def _prepare_check_line_vals(self, row, amount, payment_date, issue_date):
        Check = self.env["l10n_latam.check"]
        number = row.get("number")
        line_vals = {}

        def set_if_exists(field_name, value):
            if value and field_name in Check._fields:
                line_vals[field_name] = value

        set_if_exists("name", number)
        set_if_exists("number", number)
        set_if_exists("amount", amount)
        set_if_exists("payment_date", payment_date)
        set_if_exists("issue_date", issue_date)
        set_if_exists("emission_date", issue_date)
        set_if_exists("issuer_name", row.get("issuer_name") or "Apertura cheques terceros")
        set_if_exists("owner_name", row.get("issuer_name") or "Apertura cheques terceros")
        set_if_exists("x_studio_emisor_nombre", row.get("issuer_name") or "Apertura cheques terceros")
        set_if_exists("issuer_vat", row.get("issuer_vat"))
        set_if_exists("owner_vat", row.get("issuer_vat"))
        set_if_exists("ux_order_type", row.get("order_type") or "to_order")
        set_if_exists("memo", row.get("note"))
        set_if_exists("note", row.get("note"))
        return line_vals

    def _prepare_payment_vals(self, row, partner, amount, payment_date, issue_date):
        Payment = self.env["account.payment"]
        number = row.get("number")
        ref = _("Apertura cheque tercero %s") % number
        vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner.id if partner else False,
            "amount": amount,
            "currency_id": self.company_id.currency_id.id,
            "date": self.accounting_date,
            "journal_id": self.journal_id.id,
            "payment_method_line_id": self.payment_method_line_id.id,
            "destination_account_id": self.capital_account_id.id,
            "company_id": self.company_id.id,
            "l10n_latam_new_check_ids": [(0, 0, self._prepare_check_line_vals(row, amount, payment_date, issue_date))],
        }
        if "memo" in Payment._fields:
            vals["memo"] = ref
        elif "ref" in Payment._fields:
            vals["ref"] = ref
        return vals

    def _check_duplicate(self, number):
        Check = self.env["l10n_latam.check"].with_company(self.company_id).with_context(allowed_company_ids=[self.company_id.id])
        domain = [("name", "=", number)]
        if "company_id" in Check._fields:
            domain.append(("company_id", "=", self.company_id.id))
        existing = Check.search(domain, limit=1)
        if existing:
            raise UserError(_("Ya existe un cheque de terceros con número '%s' en esta compañía.") % number)

    def action_import(self):
        self.ensure_one()
        self._validate_configuration()

        rows = list(self._iter_csv_rows())
        if not rows:
            raise UserError(_("No hay filas para importar."))

        ctx = dict(self.env.context, allowed_company_ids=[self.company_id.id], force_company=self.company_id.id)
        wizard = self.with_company(self.company_id).with_context(ctx)
        partner = wizard._get_or_create_opening_partner()

        total = 0.0
        created_payments = self.env["account.payment"]
        summary_lines = []
        payment_account = self.payment_method_line_id.payment_account_id

        for row in rows:
            line_number = row["_line_number"]
            number = row.get("number")
            if not number:
                raise UserError(_("Línea %s: falta número de cheque.") % line_number)
            amount = wizard._parse_amount(row.get("amount"), line_number)
            payment_date = wizard._parse_date(row.get("payment_date"), line_number, required=True)
            issue_date = wizard._parse_date(row.get("issue_date"), line_number, required=False)
            total += amount

            wizard._check_duplicate(number)

            if not wizard.dry_run:
                payment_vals = wizard._prepare_payment_vals(row, partner, amount, payment_date, issue_date)
                payment = self.env["account.payment"].with_company(self.company_id).with_context(ctx).create(payment_vals)
                if wizard.post_payments:
                    payment.action_post()
                created_payments |= payment

            summary_lines.append(
                "%s | $ %.2f | vencimiento %s" % (number, amount, payment_date)
            )

        mode = "SIMULACIÓN: no se creó nada." if wizard.dry_run else "IMPORTACIÓN REAL ejecutada."
        post_status = "publicados" if wizard.post_payments else "en borrador"
        result = [
            mode,
            "Compañía: %s" % self.company_id.display_name,
            "Diario: %s" % self.journal_id.display_name,
            "Método: %s [%s]" % (
                self.payment_method_line_id.display_name,
                self.payment_method_line_id.code or self.payment_method_line_id.payment_method_id.code,
            ),
            "Debe: %s" % payment_account.display_name,
            "Haber: %s" % self.capital_account_id.display_name,
            "Cantidad de cheques: %s" % len(rows),
            "Total: $ %.2f" % total,
            "Pagos: %s" % post_status,
        ]
        if not wizard.dry_run:
            result.append("Pagos creados: %s" % len(created_payments))
        result.append("")
        result.append("Detalle:")
        result.extend(summary_lines)

        wizard.result = "\n".join(result)
        return {
            "type": "ir.actions.act_window",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
