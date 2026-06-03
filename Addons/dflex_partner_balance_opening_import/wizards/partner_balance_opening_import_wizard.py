# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DflexPartnerBalanceOpeningImportWizard(models.TransientModel):
    _name = "dflex.partner.balance.opening.import.wizard"
    _description = "Importar saldos iniciales de contactos"

    company_id = fields.Many2one(
        "res.company", string="Compañía", required=True, default=lambda self: self.env.company
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de apertura",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    accounting_date = fields.Date(
        string="Fecha contable", required=True, default=fields.Date.context_today
    )
    capital_account_id = fields.Many2one(
        "account.account",
        string="Cuenta Capital integrado",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    fca_receivable_account_id = fields.Many2one(
        "account.account",
        string="Cuenta clientes FCA",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    interno_receivable_account_id = fields.Many2one(
        "account.account",
        string="Cuenta clientes Interno",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    csv_file = fields.Binary(string="Archivo CSV", required=True)
    csv_filename = fields.Char(string="Nombre archivo")
    dry_run = fields.Boolean(string="Solo simular, no crear nada", default=True)
    post_moves = fields.Boolean(string="Publicar asientos", default=False)
    create_missing_partners = fields.Boolean(
        string="Crear contactos faltantes",
        default=False,
        help="Si no encuentra el contacto por CUIT o nombre, lo crea. Recomendado: usar solo si ya revisaste la simulación.",
    )
    result = fields.Text(string="Resultado", readonly=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        for wizard in self:
            if not wizard.company_id:
                continue
            account = wizard._find_account_by_code("3.1.1.01.002")
            if account:
                wizard.capital_account_id = account

    def _account_company_ok(self, account):
        self.ensure_one()
        if not account:
            return False
        if "company_ids" in account._fields:
            return self.company_id in account.company_ids
        if "company_id" in account._fields:
            return account.company_id == self.company_id
        return True

    def _find_account_by_code(self, code):
        Account = self.env["account.account"].with_company(self.company_id).with_context(
            allowed_company_ids=[self.company_id.id]
        )
        domain = [("code", "=", code)]
        if "company_ids" in Account._fields:
            domain.append(("company_ids", "in", self.company_id.id))
        elif "company_id" in Account._fields:
            domain.append(("company_id", "=", self.company_id.id))
        return Account.search(domain, limit=1)

    def _validate_configuration(self):
        self.ensure_one()
        if self.journal_id.company_id != self.company_id:
            raise UserError(_("El diario de apertura no pertenece a la compañía seleccionada."))
        for label, account in [
            (_("Capital integrado"), self.capital_account_id),
            (_("Clientes FCA"), self.fca_receivable_account_id),
            (_("Clientes Interno"), self.interno_receivable_account_id),
        ]:
            if not self._account_company_ok(account):
                raise UserError(_("La cuenta %s no pertenece a la compañía seleccionada.") % label)

    def _decode_csv(self):
        raw = base64.b64decode(self.csv_file or b"")
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UserError(_("No se pudo leer el CSV. Guardalo como UTF-8 o ANSI/Latin-1."))

    def _normalize_header(self, name):
        key = (name or "").strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "grupo": "grupo",
            "tipo": "grupo",
            "razsoc": "razsoc",
            "razon_social": "razsoc",
            "razón_social": "razsoc",
            "cliente": "razsoc",
            "contacto": "razsoc",
            "nombre": "razsoc",
            "cuit": "cuit",
            "vat": "cuit",
            "saldoant": "saldo",
            "saldo": "saldo",
            "importe": "saldo",
            "monto": "saldo",
            "nota": "nota",
            "observacion": "nota",
            "observación": "nota",
            "source_row": "source_row",
            "warnings": "warnings",
        }
        return aliases.get(key, key)

    def _iter_csv_rows(self):
        text = self._decode_csv()
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,	,")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))
        normalized = {name: self._normalize_header(name) for name in reader.fieldnames}
        required = {"grupo", "razsoc", "saldo"}
        missing = required - set(normalized.values())
        if missing:
            raise UserError(_("Faltan columnas obligatorias: %s") % ", ".join(sorted(missing)))
        for line_number, row in enumerate(reader, start=2):
            data = {}
            for original, value in row.items():
                if original is None:
                    continue
                key = normalized.get(original)
                if key:
                    data[key] = (value or "").strip()
            if not any(data.values()):
                continue
            data["_line_number"] = line_number
            yield data

    def _parse_amount(self, value, line_number):
        if not value:
            raise UserError(_("Línea %s: falta saldo.") % line_number)
        clean = re.sub(r"[^0-9,\.\-]", "", str(value))
        if "," in clean and "." in clean:
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(",", ".")
        try:
            return Decimal(clean)
        except InvalidOperation:
            raise UserError(_("Línea %s: saldo inválido: %s") % (line_number, value))

    def _clean_cuit(self, value):
        digits = re.sub(r"\D", "", str(value or ""))
        if digits in ("", "0", "00000000000"):
            return ""
        return digits if len(digits) == 11 else ""

    def _strip_accents(self, value):
        return "".join(
            c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c)
        )

    def _normalize_name(self, value):
        text = self._strip_accents(value or "").upper()
        text = re.sub(r"\([^)]*\)", "", text)
        text = text.replace("&", " Y ")
        text = re.sub(r"[^A-Z0-9]+", " ", text)
        words = [
            w for w in text.split()
            if w not in {"SAS", "SA", "SRL", "SACI", "SACIFIA", "SACFII", "CC", "INHABILITADA", "NOOO"}
        ]
        return " ".join(words)

    def _find_partner(self, name, cuit):
        Partner = self.env["res.partner"].with_company(self.company_id).with_context(
            allowed_company_ids=[self.company_id.id]
        )
        if cuit:
            partner = Partner.search([("vat", "=", cuit)], limit=1)
            if partner:
                return partner, "vat"
        clean_name = (name or "").strip()
        if clean_name:
            partner = Partner.search([("name", "=ilike", clean_name)], limit=1)
            if partner:
                return partner, "name_exact"
            base_name = re.sub(r"\([^)]*\)", "", clean_name).strip()
            if base_name and base_name != clean_name:
                partner = Partner.search([("name", "=ilike", base_name)], limit=1)
                if partner:
                    return partner, "name_without_comment"
            # last controlled fallback: same normalized name among limited ilike candidates
            first_token = base_name.split()[0] if base_name else clean_name.split()[0]
            candidates = Partner.search([("name", "ilike", first_token)], limit=80)
            target_norm = self._normalize_name(clean_name)
            for candidate in candidates:
                if self._normalize_name(candidate.name) == target_norm:
                    return candidate, "name_normalized"
        return self.env["res.partner"], "not_found"

    def _create_partner(self, name, cuit):
        vals = {"name": name or cuit or "Contacto apertura sin nombre"}
        if cuit:
            vals["vat"] = cuit
        return self.env["res.partner"].with_company(self.company_id).with_context(
            allowed_company_ids=[self.company_id.id]
        ).create(vals)

    def _prepare_partner_line_vals(self, row, partner, amount):
        group = row["grupo"].strip().upper()
        receivable_account = self.fca_receivable_account_id if group == "FCA" else self.interno_receivable_account_id
        name = row.get("razsoc") or partner.display_name
        ref = "Apertura saldo cliente %s - %s" % (group, name)
        abs_amount = abs(amount)
        if amount >= 0:
            partner_debit, partner_credit = abs_amount, Decimal("0.00")
        else:
            partner_debit, partner_credit = Decimal("0.00"), abs_amount

        return (0, 0, {
            "name": ref,
            "account_id": receivable_account.id,
            "partner_id": partner.id,
            "debit": float(partner_debit),
            "credit": float(partner_credit),
        })

    def _prepare_capital_line_vals(self, label, debit, credit):
        return (0, 0, {
            "name": label,
            "account_id": self.capital_account_id.id,
            "debit": float(debit),
            "credit": float(credit),
        })

    def _prepare_opening_move_vals(self, line_ids):
        return {
            "move_type": "entry",
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date": self.accounting_date,
            "ref": "Apertura saldos iniciales clientes FCA/Interno",
            "line_ids": line_ids,
        }

    def action_import(self):
        self.ensure_one()
        self._validate_configuration()
        rows = list(self._iter_csv_rows())
        if not rows:
            raise UserError(_("No hay filas para importar."))

        ctx = dict(self.env.context, allowed_company_ids=[self.company_id.id], force_company=self.company_id.id)
        wizard = self.with_company(self.company_id).with_context(ctx)
        Move = self.env["account.move"].with_company(self.company_id).with_context(ctx)

        result_lines = []
        errors = []
        created_moves = self.env["account.move"]
        totals = {"FCA": Decimal("0.00"), "INTERNO": Decimal("0.00")}
        counts = {"FCA": 0, "INTERNO": 0}
        missing_partners = []
        move_line_ids = []
        capital_debit_total = Decimal("0.00")
        capital_credit_total = Decimal("0.00")

        for row in rows:
            line_number = row["_line_number"]
            group = (row.get("grupo") or "").strip().upper()
            if group not in ("FCA", "INTERNO"):
                errors.append(_("Línea %s: grupo inválido '%s'. Use FCA o INTERNO.") % (line_number, group))
                continue
            name = row.get("razsoc") or ""
            cuit = wizard._clean_cuit(row.get("cuit"))
            amount = wizard._parse_amount(row.get("saldo"), line_number)
            if amount == 0:
                continue

            partner, match_method = wizard._find_partner(name, cuit)
            if not partner:
                if wizard.create_missing_partners and not wizard.dry_run:
                    partner = wizard._create_partner(name, cuit)
                    match_method = "created"
                else:
                    missing_partners.append("Línea %s | %s | CUIT %s" % (line_number, name, cuit or "sin CUIT"))
                    match_method = "not_found"

            counts[group] += 1
            totals[group] += amount
            result_lines.append(
                "%s | %s | $ %.2f | %s | %s" % (group, name, amount, cuit or "sin CUIT", match_method)
            )

            if partner:
                move_line_ids.append(wizard._prepare_partner_line_vals(row, partner, amount))
                if amount >= 0:
                    capital_credit_total += abs(amount)
                else:
                    capital_debit_total += abs(amount)

        if missing_partners and not wizard.create_missing_partners:
            errors.append(
                _("Contactos no encontrados. Activá 'Crear contactos faltantes' solo si ya revisaste la simulación, o corregí/importá esos contactos primero.\n%s")
                % "\n".join(missing_partners[:80])
            )

        mode = "SIMULACIÓN: no se creó nada." if wizard.dry_run else "IMPORTACIÓN REAL ejecutada."
        post_status = "publicado" if wizard.post_moves else "en borrador"
        output = [
            mode,
            "Compañía: %s" % wizard.company_id.display_name,
            "Diario apertura: %s" % wizard.journal_id.display_name,
            "Capital integrado: %s" % wizard.capital_account_id.display_name,
            "Cuenta FCA: %s" % wizard.fca_receivable_account_id.display_name,
            "Cuenta Interno: %s" % wizard.interno_receivable_account_id.display_name,
            "Cantidad FCA: %s | Total FCA: $ %.2f" % (counts["FCA"], totals["FCA"]),
            "Cantidad Interno: %s | Total Interno: $ %.2f" % (counts["INTERNO"], totals["INTERNO"]),
            "Total general: $ %.2f" % (totals["FCA"] + totals["INTERNO"]),
            "Asiento: único, %s" % post_status,
            "Líneas de cliente: %s" % len(move_line_ids),
            "Capital integrado al Debe: $ %.2f" % capital_debit_total,
            "Capital integrado al Haber: $ %.2f" % capital_credit_total,
        ]

        if errors:
            output.append("")
            output.append("ADVERTENCIAS / ERRORES:")
            output.extend(errors)

        # In real mode, block imports when there are missing partners or validation errors.
        if errors and not wizard.dry_run:
            raise UserError("\n".join(errors))

        if not wizard.dry_run:
            capital_label = "Apertura saldos clientes - Capital integrado"
            if capital_debit_total:
                move_line_ids.append(wizard._prepare_capital_line_vals(capital_label, capital_debit_total, Decimal("0.00")))
            if capital_credit_total:
                move_line_ids.append(wizard._prepare_capital_line_vals(capital_label, Decimal("0.00"), capital_credit_total))

            if not move_line_ids:
                raise UserError(_("No hay líneas con saldo distinto de cero para crear el asiento."))

            move = Move.create(wizard._prepare_opening_move_vals(move_line_ids))
            if wizard.post_moves:
                move.action_post()
            created_moves |= move
            output.append("Asiento creado: %s" % (move.display_name or move.name or move.id))

        output.append("")
        output.append("Detalle:")
        output.extend(result_lines[:250])
        wizard.result = "\n".join(output)

        return {
            "type": "ir.actions.act_window",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
