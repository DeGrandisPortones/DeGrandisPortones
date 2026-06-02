# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
import unicodedata
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DflexOwnCheckOpeningImportWizard(models.TransientModel):
    _name = "dflex.own.check.opening.import.wizard"
    _description = "Importar cheques propios en circulacion"

    file = fields.Binary(string="Archivo CSV", required=True, attachment=False)
    filename = fields.Char(string="Nombre del archivo")
    company_id = fields.Many2one(
        "res.company",
        string="Compania",
        required=True,
        default=lambda self: self.env.company,
    )
    bank_journal_id = fields.Many2one(
        "account.journal",
        string="Diario banco que emite los cheques",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    opening_journal_id = fields.Many2one(
        "account.journal",
        string="Diario para asiento de alta",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        help="Diario donde se crea el asiento inicial: Debe Capital integrado / Haber Cheques propios.",
    )
    capital_account_id = fields.Many2one(
        "account.account",
        string="Cuenta Capital integrado",
        required=True,
        help="Cuenta que se debita al cargar los cheques en circulacion. Ejemplo: 3.1.1.01.002.",
    )
    own_check_account_id = fields.Many2one(
        "account.account",
        string="Cuenta puente Cheques propios",
        help="Si se deja vacia, se toma de Pagos salientes > Cheques propios del diario banco.",
    )
    dry_run = fields.Boolean(
        string="Solo simular, no crear nada",
        default=True,
        help="Mantener activo para validar el CSV sin crear cheques ni asientos.",
    )
    post_opening_moves = fields.Boolean(
        string="Publicar asientos de alta",
        default=False,
        help="Si esta desmarcado, los asientos quedan en borrador para revisar antes de publicar.",
    )
    skip_existing = fields.Boolean(
        string="Omitir cheques existentes",
        default=False,
        help="Si un cheque ya existe para el diario y compania, se omite en vez de abortar.",
    )
    create_partners = fields.Boolean(
        string="Crear proveedores si no existen",
        default=False,
    )

    @api.onchange("bank_journal_id")
    def _onchange_bank_journal_id(self):
        for wizard in self:
            if wizard.bank_journal_id:
                wizard.own_check_account_id = wizard._get_own_check_account_from_journal(wizard.bank_journal_id)
            else:
                wizard.own_check_account_id = False

    def action_import(self):
        self.ensure_one()
        self._validate_company_records()
        rows = self._read_csv_rows()
        prepared, skipped = self._prepare_rows(rows)

        total = sum(row["amount"] for row in prepared)
        if self.dry_run:
            return self._notify(
                _("Simulacion correcta"),
                _(
                    "No se creo nada. Filas validas: %(count)s. Omitidas: %(skipped)s. Total: %(total).2f."
                )
                % {"count": len(prepared), "skipped": skipped, "total": total},
                sticky=True,
            )

        checks, moves = self._create_checks_and_moves(prepared)
        return self._notify(
            _("Importacion finalizada"),
            _(
                "Se crearon %(checks)s cheques propios y %(moves)s asientos de alta. Omitidos: %(skipped)s. Total: %(total).2f."
            )
            % {"checks": len(checks), "moves": len(moves), "skipped": skipped, "total": total},
            sticky=True,
        )

    def _notify(self, title, message, sticky=False):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "success",
                "sticky": sticky,
            },
        }

    def _validate_company_records(self):
        company = self.company_id
        if self.bank_journal_id.company_id != company:
            raise UserError(_("El diario banco no pertenece a la compania seleccionada."))
        if self.opening_journal_id.company_id != company:
            raise UserError(_("El diario de alta no pertenece a la compania seleccionada."))
        if not self.bank_journal_id.default_account_id:
            raise UserError(_("El diario banco no tiene cuenta bancaria/default configurada."))

        pending_account = self.own_check_account_id or self._get_own_check_account_from_journal(self.bank_journal_id)
        if not pending_account:
            raise UserError(
                _(
                    "No se encontro cuenta puente de Cheques propios. Configurala en Pagos salientes > Cheques propios del diario banco, o seleccionala manualmente."
                )
            )
        self._check_account_company(self.capital_account_id, company, _("Capital integrado"))
        self._check_account_company(pending_account, company, _("Cheques propios"))
        self._check_account_company(self.bank_journal_id.default_account_id, company, _("Banco"))
        if self.capital_account_id == pending_account:
            raise UserError(_("La cuenta Capital integrado y la cuenta puente Cheques propios no pueden ser la misma."))

    def _check_account_company(self, account, company, label):
        if not account:
            raise UserError(_("Falta configurar la cuenta %(label)s.") % {"label": label})
        if "company_id" in account._fields and account.company_id and account.company_id != company:
            raise UserError(_("La cuenta %(account)s no pertenece a %(company)s.") % {
                "account": account.display_name,
                "company": company.display_name,
            })
        if "company_ids" in account._fields and account.company_ids and company not in account.company_ids:
            raise UserError(_("La cuenta %(account)s no esta habilitada para %(company)s.") % {
                "account": account.display_name,
                "company": company.display_name,
            })

    def _get_own_check_account_from_journal(self, journal):
        method_lines = journal.outbound_payment_method_line_ids.filtered(
            lambda line: (
                line.code == "own_checks"
                or line.payment_method_id.code == "own_checks"
                or "cheques propios" in " ".join(
                    part for part in [line.name, line.payment_method_id.name] if part
                ).lower()
                or "own check" in " ".join(part for part in [line.name, line.payment_method_id.name] if part).lower()
            )
        )
        return method_lines.filtered("payment_account_id")[:1].payment_account_id

    def _read_csv_rows(self):
        try:
            csv_bytes = base64.b64decode(self.file)
            text = csv_bytes.decode("utf-8-sig")
        except Exception as exc:
            raise UserError(_("No se pudo leer el CSV. Guardalo como UTF-8. Error: %s") % exc)

        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        rows = []
        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            normalized = {self._normalize_key(key): value for key, value in row.items() if key}
            normalized["__line__"] = index
            rows.append(normalized)
        if not rows:
            raise UserError(_("El CSV no tiene filas para importar."))
        return rows

    def _prepare_rows(self, rows):
        company = self.company_id
        pending_account = self.own_check_account_id or self._get_own_check_account_from_journal(self.bank_journal_id)
        prepared = []
        errors = []
        skipped = 0

        Check = self.env["dflex.check"].with_context(
            allowed_company_ids=[company.id], default_company_id=company.id
        ).with_company(company)

        for row in rows:
            line = row.get("__line__")
            try:
                number_text = self._cell(row, "number", required=True)
                number = self._parse_number(number_text)
                amount = self._parse_amount(self._cell(row, "amount", required=True))
                if amount <= 0:
                    raise UserError(_("El importe debe ser mayor a cero."))

                existing = Check.search([
                    ("number", "=", number),
                    ("journal_id", "=", self.bank_journal_id.id),
                    ("company_id", "=", company.id),
                ], limit=1)
                if existing:
                    if self.skip_existing:
                        skipped += 1
                        continue
                    raise UserError(_("Ya existe el cheque %(check)s para este diario y compania.") % {
                        "check": existing.display_name,
                    })

                issue_date = self._parse_date(self._cell(row, "issue_date"))
                payment_date = self._parse_date(self._cell(row, "payment_date"))
                delivery_date = self._parse_date(self._cell(row, "delivery_date"))
                state = self._parse_state(self._cell(row, "state"), payment_date)
                check_type = self._parse_check_type(self._cell(row, "type"))
                partner = self._find_or_create_partner(row)

                prepared.append({
                    "name": str(number_text).strip(),
                    "number": number,
                    "amount": amount,
                    "issue_date": issue_date,
                    "payment_date": payment_date,
                    "delivery_date": delivery_date or issue_date or fields.Date.context_today(self),
                    "state": state,
                    "type": check_type,
                    "partner": partner,
                    "note": self._cell(row, "note"),
                    "pending_account": pending_account,
                })
            except Exception as exc:
                errors.append(_("Linea %(line)s: %(error)s") % {"line": line, "error": exc})

        if errors:
            raise UserError(_("No se importo nada porque hay errores:\n%s") % "\n".join(errors[:25]))
        if not prepared and not skipped:
            raise UserError(_("No hay filas validas para importar."))
        return prepared, skipped

    def _create_checks_and_moves(self, prepared):
        company = self.company_id
        Check = self.env["dflex.check"].with_context(
            allowed_company_ids=[company.id], default_company_id=company.id
        ).with_company(company)
        Move = self.env["account.move"].with_context(
            allowed_company_ids=[company.id], default_company_id=company.id, default_move_type="entry"
        ).with_company(company)

        checks = Check.browse()
        moves = Move.browse()
        for row in prepared:
            partner = row["partner"]
            check = Check.create({
                "name": row["name"],
                "number": row["number"],
                "journal_id": self.bank_journal_id.id,
                "type": row["type"],
                "issue_date": row["issue_date"],
                "payment_date": row["payment_date"],
                "delivery_date": row["delivery_date"],
                "amount": row["amount"],
                "currency_id": company.currency_id.id,
                "partner_id": partner.id if partner else False,
                "state": row["state"],
                "company_id": company.id,
                "note": row["note"],
            })

            ref = _("Alta cheque propio en circulacion %s") % check.name
            move = Move.create({
                "move_type": "entry",
                "journal_id": self.opening_journal_id.id,
                "date": row["issue_date"] or row["delivery_date"] or fields.Date.context_today(self),
                "ref": ref,
                "company_id": company.id,
                "line_ids": [
                    (0, 0, {
                        "name": ref,
                        "account_id": self.capital_account_id.id,
                        "partner_id": partner.id if partner else False,
                        "debit": row["amount"],
                        "credit": 0.0,
                    }),
                    (0, 0, {
                        "name": ref,
                        "account_id": row["pending_account"].id,
                        "partner_id": partner.id if partner else False,
                        "debit": 0.0,
                        "credit": row["amount"],
                    }),
                ],
            })
            if self.post_opening_moves:
                move.action_post()
            check.move_id = move.id
            checks |= check
            moves |= move
        return checks, moves

    def _find_or_create_partner(self, row):
        vat = (self._cell(row, "partner_vat") or "").strip()
        name = (self._cell(row, "partner_name") or "").strip()
        Partner = self.env["res.partner"].with_context(allowed_company_ids=[self.company_id.id])

        partner = Partner.browse()
        if vat:
            partner = Partner.search([("vat", "=", vat)], limit=1)
        if not partner and name:
            partner = Partner.search([("name", "=", name)], limit=1)
        if not partner and self.create_partners and (name or vat):
            partner = Partner.create({
                "name": name or vat,
                "vat": vat or False,
                "company_type": "company",
                "company_id": self.company_id.id,
            })
        return partner

    def _cell(self, row, field_name, required=False):
        aliases = {
            "number": ["number", "numero", "nro", "n_cheque", "nro_cheque", "cheque", "numero_cheque"],
            "amount": ["amount", "importe", "monto", "valor"],
            "payment_date": ["payment_date", "fecha_pago", "fecha_de_pago", "vencimiento", "fecha_vencimiento"],
            "issue_date": ["issue_date", "fecha_emision", "emision", "fecha_de_emision"],
            "delivery_date": ["delivery_date", "fecha_entrega", "fecha_de_entrega"],
            "partner_vat": ["partner_vat", "vat", "cuit", "cuit_proveedor", "cuit_beneficiario"],
            "partner_name": ["partner_name", "proveedor", "entregado_a", "beneficiario", "nombre", "razon_social"],
            "type": ["type", "tipo", "tipo_cheque"],
            "state": ["state", "estado"],
            "note": ["note", "notas", "observacion", "observaciones", "detalle"],
        }[field_name]
        for alias in aliases:
            if alias in row and row[alias] not in (None, ""):
                return row[alias]
        if required:
            raise UserError(_("Falta la columna obligatoria: %s") % field_name)
        return False

    def _parse_number(self, value):
        text = str(value or "").strip()
        digits = re.sub(r"\D", "", text)
        if not digits:
            raise UserError(_("Numero de cheque invalido: %s") % text)
        return int(digits)

    def _parse_amount(self, value):
        text = str(value or "").strip()
        text = text.replace("$", "").replace(" ", "")
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            return float(text)
        except Exception:
            raise UserError(_("Importe invalido: %s") % value)

    def _parse_date(self, value):
        if not value:
            return False
        text = str(value).strip()
        for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, date_format).date()
            except ValueError:
                continue
        raise UserError(_("Fecha invalida '%s'. Usar YYYY-MM-DD o DD/MM/YYYY.") % text)

    def _parse_state(self, value, payment_date):
        if value:
            normalized = self._normalize_key(value)
            mapping = {
                "entregado": "delivered",
                "delivered": "delivered",
                "en_circulacion": "delivered",
                "circulacion": "delivered",
                "por_ingresar": "pending_entry",
                "pending_entry": "pending_entry",
                "vencido": "expired",
                "vencidos": "expired",
                "expired": "expired",
            }
            state = mapping.get(normalized)
            if not state:
                raise UserError(_("Estado invalido: %s") % value)
            return state

        today = fields.Date.context_today(self)
        if payment_date:
            if today >= payment_date + relativedelta(months=1):
                return "expired"
            if today >= payment_date:
                return "pending_entry"
        return "delivered"

    def _parse_check_type(self, value):
        if not value:
            return "fisico"
        normalized = self._normalize_key(value)
        if normalized in ("echeq", "e_cheq", "echeck", "e_check", "electronico"):
            return "echeq"
        return "fisico"

    def _normalize_key(self, value):
        text = str(value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")
