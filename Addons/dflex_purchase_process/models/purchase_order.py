from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    dflex_purchase_process_state = fields.Selection(
        [
            ("authorized", "Autorizada"),
            ("in_process", "En Proceso"),
            ("received", "Recibida"),
            ("paid", "Pagada"),
            ("redo", "Rehacer la orden"),
        ],
        string="Estado compras",
        copy=False,
        index=True,
        tracking=True,
        help=(
            "Estado operativo interno de Compras. "
            "No reemplaza el estado contable/nativo de Odoo."
        ),
    )
    dflex_purchase_process_user_id = fields.Many2one(
        "res.users",
        string="Responsable compras",
        copy=False,
        tracking=True,
    )
    dflex_purchase_authorized_date = fields.Datetime(
        string="Fecha autorización",
        copy=False,
        readonly=True,
    )
    dflex_purchase_in_process_date = fields.Datetime(
        string="Fecha en proceso",
        copy=False,
        readonly=True,
    )
    dflex_purchase_received_date = fields.Datetime(
        string="Fecha recibida",
        copy=False,
        readonly=True,
    )
    dflex_purchase_redo_date = fields.Datetime(
        string="Fecha rehacer orden",
        copy=False,
        readonly=True,
    )
    dflex_purchase_paid_date = fields.Datetime(
        string="Fecha pagada",
        copy=False,
        readonly=True,
    )
    dflex_execution_deadline_date = fields.Date(
        string="Fecha límite de ejecución",
        copy=False,
        tracking=True,
        help="Fecha límite que carga Administración al autorizar la compra.",
    )
    dflex_purchase_executed = fields.Boolean(
        string="Ejecutada con proveedor",
        copy=False,
        tracking=True,
        help="Debe tildarlo Compras cuando ejecuta la compra con el proveedor.",
    )
    dflex_purchase_executed_date = fields.Datetime(
        string="Fecha ejecutada",
        copy=False,
        readonly=True,
    )
    dflex_purchase_executed_user_id = fields.Many2one(
        "res.users",
        string="Ejecutada por",
        copy=False,
        readonly=True,
    )
    dflex_purchase_redo_deadline_date = fields.Date(
        string="Vence control de cotización",
        compute="_compute_dflex_purchase_redo_deadline_date",
        store=True,
        help="Fecha límite + 15 días corridos.",
    )

    @api.depends("date_order")
    def _compute_dflex_purchase_redo_deadline_date(self):
        for order in self:
            deadline = order._dflex_get_order_deadline_date()
            order.dflex_purchase_redo_deadline_date = deadline + timedelta(days=15) if deadline else False

    def _dflex_get_order_deadline_date(self):
        """Return the order deadline date used to trigger Rehacer la orden.

        In Odoo Purchase, date_order is labelled as Order Deadline / Fecha límite
        in RFQ/purchase flows. If a database later adds a custom deadline field,
        the method can be extended safely.
        """
        self.ensure_one()
        value = self.date_order
        if isinstance(value, datetime):
            return value.date()
        return value or False

    def _dflex_should_mark_redo(self, today=None):
        self.ensure_one()
        if self.state in ("cancel", "done"):
            return False
        if self.dflex_purchase_process_state in ("received", "paid"):
            return False

        deadline = self._dflex_get_order_deadline_date()
        if not deadline:
            return False

        today = today or fields.Date.context_today(self)
        return today >= (deadline + timedelta(days=15))

    def _dflex_set_purchase_process_state(self, state, message=None):
        vals = {
            "dflex_purchase_process_state": state,
            "dflex_purchase_process_user_id": self.env.user.id,
        }
        now = fields.Datetime.now()
        if state == "authorized":
            vals["dflex_purchase_authorized_date"] = now
        elif state == "in_process":
            vals["dflex_purchase_in_process_date"] = now
        elif state == "received":
            vals["dflex_purchase_received_date"] = now
        elif state == "redo":
            vals["dflex_purchase_redo_date"] = now
        elif state == "paid":
            vals["dflex_purchase_paid_date"] = now

        self.write(vals)
        if message:
            self.message_post(body=message)

    def _dflex_protect_deadline_dates_in_vals(self, vals):
        """Evita que Odoo/Studio borre fechas límite al confirmar/aprobar.

        Permite cambiar la fecha por otra fecha, pero si llega un write con
        date_order=False o dflex_execution_deadline_date=False y el registro ya
        tenía valor, se ignora ese borrado.
        """
        if self.env.context.get("dflex_allow_clear_deadline_dates"):
            return vals

        protected_vals = dict(vals)

        if (
            "date_order" in protected_vals
            and not protected_vals.get("date_order")
            and any(self.mapped("date_order"))
        ):
            protected_vals.pop("date_order", None)

        if (
            "dflex_execution_deadline_date" in protected_vals
            and not protected_vals.get("dflex_execution_deadline_date")
            and any(self.mapped("dflex_execution_deadline_date"))
        ):
            protected_vals.pop("dflex_execution_deadline_date", None)

        return protected_vals

    def _dflex_get_deadline_snapshot(self):
        """Guarda fechas límite antes de autorizar/confirmar."""
        snapshot = {}
        for order in self:
            snapshot[order.id] = {
                "date_order": order.date_order,
                "dflex_execution_deadline_date": order.dflex_execution_deadline_date,
            }
        return snapshot

    def _dflex_restore_deadline_snapshot(self, snapshot):
        for order in self:
            values = snapshot.get(order.id, {})
            vals = {}

            old_date_order = values.get("date_order")
            old_execution_deadline = values.get("dflex_execution_deadline_date")

            if old_date_order and not order.date_order:
                vals["date_order"] = old_date_order
            if old_execution_deadline and not order.dflex_execution_deadline_date:
                vals["dflex_execution_deadline_date"] = old_execution_deadline

            if vals:
                order.with_context(dflex_skip_deadline_restore=True).write(vals)

    def _dflex_get_related_vendor_bills(self):
        self.ensure_one()
        bills = self.env["account.move"]

        if "invoice_ids" in self._fields:
            bills |= self.invoice_ids

        purchase_lines = self.order_line
        invoice_lines = purchase_lines.mapped("invoice_lines")
        if invoice_lines:
            bills |= invoice_lines.mapped("move_id")

        return bills.filtered(lambda move: move.move_type in ("in_invoice", "in_refund") and move.state != "cancel")

    def _dflex_is_purchase_paid(self):
        self.ensure_one()
        bills = self._dflex_get_related_vendor_bills()
        posted_bills = bills.filtered(lambda move: move.state == "posted")
        if not posted_bills:
            return False

        # En Odoo, cuando Administración registra el pago puede quedar "in_payment"
        # hasta la conciliación bancaria. Para el seguimiento operativo de Compras,
        # ambos estados se consideran Pagada.
        return all(move.payment_state in ("paid", "in_payment") for move in posted_bills)

    def _dflex_update_paid_state_from_bills(self):
        for order in self:
            if order._dflex_is_purchase_paid() and order.dflex_purchase_process_state != "paid":
                order._dflex_set_purchase_process_state(
                    "paid",
                    _("La orden fue marcada como Pagada porque sus facturas de proveedor están pagadas/en pago."),
                )

    def _dflex_user_has_group_safe(self, xmlid):
        try:
            return self.env.user.has_group(xmlid)
        except Exception:
            return False

    def _dflex_user_can_execute_after_deadline(self):
        self.ensure_one()
        return bool(
            self._dflex_user_has_group_safe("account.group_account_manager")
            or self._dflex_user_has_group_safe("base.group_system")
        )

    def _dflex_validate_execution_deadline(self, vals):
        if not vals.get("dflex_purchase_executed"):
            return

        today = fields.Date.context_today(self)
        for order in self:
            deadline = vals.get("dflex_execution_deadline_date") or order.dflex_execution_deadline_date
            if deadline and isinstance(deadline, str):
                deadline = fields.Date.to_date(deadline)

            if deadline and today > deadline and not order._dflex_user_can_execute_after_deadline():
                raise UserError(
                    _(
                        "No podés marcar la compra %s como ejecutada porque la fecha límite de ejecución (%s) ya pasó. "
                        "Debe marcarla Administración."
                    )
                    % (order.display_name, deadline)
                )

    def action_dflex_mark_executed(self):
        self.write({"dflex_purchase_executed": True})
        return True

    def action_dflex_unmark_executed(self):
        self.write({"dflex_purchase_executed": False})
        return True

    def action_dflex_set_authorized(self):
        deadline_snapshot = self._dflex_get_deadline_snapshot()
        for order in self:
            order._dflex_set_purchase_process_state(
                "authorized",
                _("Compra marcada como Autorizada por %s.") % self.env.user.display_name,
            )
        self._dflex_restore_deadline_snapshot(deadline_snapshot)
        return True

    def action_dflex_set_in_process(self):
        for order in self:
            if order.dflex_purchase_process_state == "received":
                raise UserError(_("No se puede pasar a En Proceso una orden que ya está Recibida."))
            order._dflex_set_purchase_process_state(
                "in_process",
                _("Compras inició la gestión con el proveedor."),
            )
        return True

    def action_dflex_set_received(self):
        for order in self:
            if order.dflex_purchase_process_state == "redo":
                raise UserError(
                    _("La orden está en Rehacer la orden. Primero actualizá la cotización/presupuesto.")
                )
            order._dflex_set_purchase_process_state(
                "received",
                _("Compras marcó la orden como Recibida / acuse de recibo confirmado."),
            )
        return True

    def action_dflex_set_paid(self):
        for order in self:
            order._dflex_set_purchase_process_state(
                "paid",
                _("Compra marcada como Pagada por %s.") % self.env.user.display_name,
            )
        return True

    def action_dflex_force_redo(self):
        for order in self:
            order._dflex_set_purchase_process_state(
                "redo",
                _("La orden debe rehacerse y actualizar cotización/presupuesto."),
            )
        return True

    @api.model
    def _cron_dflex_update_purchase_process_states(self):
        today = fields.Date.context_today(self)
        orders = self.search(
            [
                ("state", "not in", ["cancel", "done"]),
                ("date_order", "!=", False),
                ("dflex_purchase_process_state", "not in", ["received", "paid"]),
            ]
        )
        to_redo = orders.filtered(lambda order: order._dflex_should_mark_redo(today=today))
        for order in to_redo:
            if order.dflex_purchase_process_state != "redo":
                order._dflex_set_purchase_process_state(
                    "redo",
                    _(
                        "La orden pasó automáticamente a Rehacer la orden: "
                        "pasaron 15 días corridos desde la fecha límite de la orden."
                    ),
                )
        return True

    def button_confirm(self):
        deadline_snapshot = self._dflex_get_deadline_snapshot()
        res = super().button_confirm()
        self._dflex_restore_deadline_snapshot(deadline_snapshot)
        for order in self:
            if order.state in ("purchase", "done") and not order.dflex_purchase_process_state:
                order._dflex_set_purchase_process_state(
                    "authorized",
                    _("Compra marcada como Autorizada al confirmar la orden."),
                )
        self._dflex_update_paid_state_from_bills()
        return res

    def button_approve(self, force=False):
        deadline_snapshot = self._dflex_get_deadline_snapshot()
        res = super().button_approve(force=force)
        self._dflex_restore_deadline_snapshot(deadline_snapshot)
        for order in self:
            if order.state in ("purchase", "done") and not order.dflex_purchase_process_state:
                order._dflex_set_purchase_process_state(
                    "authorized",
                    _("Compra marcada como Autorizada al aprobar la orden."),
                )
        self._dflex_update_paid_state_from_bills()
        return res

    def button_draft(self):
        res = super().button_draft()
        self.write(
            {
                "dflex_purchase_process_state": False,
                "dflex_purchase_process_user_id": False,
                "dflex_purchase_authorized_date": False,
                "dflex_purchase_in_process_date": False,
                "dflex_purchase_received_date": False,
                "dflex_purchase_redo_date": False,
                "dflex_purchase_paid_date": False,
            }
        )
        return res

    def write(self, vals):
        vals = self._dflex_protect_deadline_dates_in_vals(vals)
        self._dflex_validate_execution_deadline(vals)

        if vals.get("dflex_purchase_executed"):
            vals = dict(vals)
            vals.setdefault("dflex_purchase_executed_date", fields.Datetime.now())
            vals.setdefault("dflex_purchase_executed_user_id", self.env.user.id)
        elif "dflex_purchase_executed" in vals and not vals.get("dflex_purchase_executed"):
            vals = dict(vals)
            vals.setdefault("dflex_purchase_executed_date", False)
            vals.setdefault("dflex_purchase_executed_user_id", False)

        res = super().write(vals)

        # Si cambian la fecha límite manualmente y la orden no está recibida,
        # recalculamos el estado operativo de manera inmediata.
        if "date_order" in vals:
            today = fields.Date.context_today(self)
            for order in self:
                if order._dflex_should_mark_redo(today=today):
                    if order.dflex_purchase_process_state != "redo":
                        order._dflex_set_purchase_process_state(
                            "redo",
                            _(
                                "La orden pasó a Rehacer la orden porque la nueva fecha límite "
                                "ya supera los 15 días corridos."
                            ),
                        )
                elif order.dflex_purchase_process_state == "redo" and order.state not in ("cancel", "done") and not order._dflex_is_purchase_paid():
                    # Si el usuario actualiza la fecha límite/cotización, vuelve a Autorizada
                    # para que Compras pueda iniciar el flujo nuevamente.
                    order._dflex_set_purchase_process_state(
                        "authorized",
                        _("La fecha límite fue actualizada; la orden vuelve a Autorizada."),
                    )
        return res
