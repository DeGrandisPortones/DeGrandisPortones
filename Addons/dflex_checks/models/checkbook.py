from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheckbook(models.Model):
    _name = "dflex.checkbook"
    _description = "Chequera de cheques propios"
    _order = "id desc"

    name = fields.Char(string="Nombre", required=True, default=lambda self: _("Chequera"))
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario banco",
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        check_company=True,
        help="Diario desde el que se emitirán los cheques de esta chequera/cartera.",
    )
    bank_id = fields.Many2one(
        "res.bank",
        string="Banco",
        compute="_compute_bank_id",
        store=True,
        readonly=False,
        help="Banco asociado al diario. Se conserva por compatibilidad con chequeras existentes.",
    )
    type = fields.Selection(
        [("fisico", "Físico"), ("echeq", "eCheq")],
        string="Tipo de cheque",
        required=True,
        default="fisico",
        help="Indica si esta chequera/cartera contiene cheques físicos o cheques electrónicos.",
    )

    start_number = fields.Integer(string="Número inicial", required=True)
    quantity = fields.Integer(string="Cantidad de cheques", required=True)
    last_number = fields.Integer(string="Último número", compute="_compute_last_number", store=True)

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company, required=True
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("generated", "Generada"), ("closed", "Cerrada")],
        default="draft",
        string="Estado",
    )

    check_ids = fields.One2many("dflex.check", "checkbook_id", string="Cheques")

    _sql_constraints = [
        (
            "start_positive",
            "CHECK(start_number > 0 AND quantity > 0)",
            "El número inicial y la cantidad deben ser positivos.",
        ),
    ]

    @api.depends("journal_id", "journal_id.bank_id")
    def _compute_bank_id(self):
        for rec in self:
            if rec.journal_id and "bank_id" in rec.journal_id._fields:
                rec.bank_id = rec.journal_id.bank_id

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        for rec in self:
            if rec.journal_id and "bank_id" in rec.journal_id._fields:
                rec.bank_id = rec.journal_id.bank_id

    @api.depends("start_number", "quantity")
    def _compute_last_number(self):
        for rec in self:
            rec.last_number = rec.start_number + rec.quantity - 1 if rec.quantity and rec.start_number else 0

    def _get_checkbook_overlap_domain(self):
        self.ensure_one()
        domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
            ("start_number", "<=", self.last_number),
            ("last_number", ">=", self.start_number),
        ]
        if self.journal_id:
            domain.append(("journal_id", "=", self.journal_id.id))
        elif self.bank_id:
            domain.append(("bank_id", "=", self.bank_id.id))
        return domain

    def action_generate_checks(self):
        for book in self:
            if book.state != "draft":
                raise ValidationError(_("Solo se pueden generar cheques desde el estado Borrador."))
            if not book.journal_id:
                raise ValidationError(_("Debe indicar el diario banco de la chequera."))

            overlap = self.search(book._get_checkbook_overlap_domain(), limit=1)
            if overlap:
                raise ValidationError(
                    _("El rango de esta chequera se solapa con otra existente (%s).") % overlap.display_name
                )

            vals_list = []
            for number in range(book.start_number, book.last_number + 1):
                vals_list.append(
                    {
                        "name": str(number),
                        "number": number,
                        "journal_id": book.journal_id.id,
                        "bank_id": book.bank_id.id if book.bank_id else False,
                        "type": book.type,
                        "company_id": book.company_id.id,
                        "checkbook_id": book.id,
                    }
                )
            self.env["dflex.check"].create(vals_list)
            book.state = "generated"

    def action_close(self):
        for book in self:
            book.state = "closed"

    @api.model
    def _assign_missing_journals_from_bank(self):
        """Best-effort migration for old records created when the model used res.bank only."""
        checkbooks = self.search([("journal_id", "=", False), ("bank_id", "!=", False)])
        for book in checkbooks:
            journal = self.env["account.journal"].search(
                [
                    ("type", "in", ["bank", "cash"]),
                    ("company_id", "=", book.company_id.id),
                    ("bank_id", "=", book.bank_id.id),
                ],
                limit=1,
            )
            if journal:
                book.journal_id = journal.id
        self.env["dflex.check"]._assign_missing_journals_from_bank()
        return True
