# stock_distirbutor_delivery_api/controllers/distributor_api.py
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorApiController(http.Controller):
    """
    API para la app del distribuidor (React, Postman, etc.).

    Endpoints:

    - GET  /distributor/api/pickings
        Lista las entregas pendientes marcadas como 'Entrega vía distribuidor'.

    - POST /distributor/api/pickings/<picking_id>/final_customer
        Guarda los datos del cliente final para esa entrega.

    - GET  /distributor/api/products
        Devuelve productos vendibles para armar el presupuesto.

    - POST /distributor/api/quotations
        Crea una cotización (sale.order) en Odoo a partir de los productos elegidos.
    """

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _json_response(self, data, status=200):
        """Devuelve respuesta JSON con cabeceras CORS abiertas para la app."""
        body = json.dumps(data, default=str)
        headers = [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ]
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    # ---------------------------------------------------------------------
    # Entregas vía distribuidor (pickings)
    # ---------------------------------------------------------------------
    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        """
        Devuelve las entregas pendientes para distribuidor.

        Dominio:
        - picking_type_id.code = 'outgoing'
        - state in ['confirmed', 'assigned']
        - is_distributor_delivery = True
        - final_customer_completed = False
        """
        if request.httprequest.method == "OPTIONS":
            # Preflight CORS
            return self._json_response({}, status=200)

        user = request.env.user
        Picking = request.env["stock.picking"].sudo().with_context(lang=user.lang)

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["confirmed", "assigned"]),
            ("is_distributor_delivery", "=", True),
            ("final_customer_completed", "=", False),
        ]

        pickings = Picking.search(domain, order="scheduled_date, id")

        data = []
        for picking in pickings:
            lines = []
            for move in picking.move_ids_without_package:
                lines.append(
                    {
                        "id": move.id,
                        "product_id": move.product_id.id,
                        "product_name": move.product_id.display_name,
                        "quantity": move.product_uom_qty,
                        "uom": move.product_uom.name,
                    }
                )

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin,
                    "scheduled_date": picking.scheduled_date,
                    "state": picking.state,
                    "partner_name": picking.partner_id.name,
                    "partner_ref": picking.partner_id.ref,
                    "is_distributor_delivery": picking.is_distributor_delivery,
                    "final_customer_completed": picking.final_customer_completed,
                    "final_customer_name": picking.final_customer_name,
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """
        Guarda los datos del cliente final para un picking concreto.

        Body esperado (JSON):
        {
            "name": "...",
            "street": "...",
            "city": "...",
            "vat": "...",
            "phone": "...",
            "email": "...",
            "notes": "..."
        }
        """
        if request.httprequest.method == "OPTIONS":
            # Preflight CORS
            return self._json_response({}, status=200)

        user = request.env.user

        # Parsear JSON del body
        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response(
                {"error": "Invalid JSON payload."},
                status=400,
            )

        Picking = request.env["stock.picking"].sudo().with_context(lang=user.lang)

        picking = Picking.search(
            [
                ("id", "=", picking_id),
                ("is_distributor_delivery", "=", True),
            ],
            limit=1,
        )

        if not picking:
            return self._json_response(
                {"error": "Picking not found or not marked for distributor."},
                status=404,
            )

        values = {
            "final_customer_name": payload.get("name"),
            "final_customer_street": payload.get("street"),
            "final_customer_city": payload.get("city"),
            "final_customer_vat": payload.get("vat"),
            "final_customer_phone": payload.get("phone"),
            "final_customer_email": payload.get("email"),
            "final_customer_notes": payload.get("notes"),
            "final_customer_completed": True,
        }

        picking.write(values)

        return self._json_response(
            {
                "success": True,
                "picking_id": picking.id,
            }
        )

    # ---------------------------------------------------------------------
    # Productos para presupuestar
    # ---------------------------------------------------------------------
    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """
        Devuelve productos vendibles.

        Opcionalmente se puede filtrar por etiqueta de producto con ?tag=NombreEtiqueta
        usando las etiquetas estándar de Odoo (product.template.tag).
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        env = request.env
        Product = env["product.product"].sudo()

        domain = [
            ("sale_ok", "=", True),
            ("active", "=", True),
        ]

        # Filtro opcional por etiqueta de producto (?tag=XXX)
        tag_name = kwargs.get("tag")
        if tag_name:
            Template = env["product.template"].sudo()
            templates = Template.search([("tag_ids.name", "=", tag_name)])
            if templates:
                domain.append(("product_tmpl_id", "in", templates.ids))
            else:
                # No hay productos con esa etiqueta
                return self._json_response({"data": []})

        products = Product.search(domain, order="default_code, name", limit=500)

        data = []
        for product in products:
            data.append(
                {
                    "id": product.id,
                    "name": product.display_name,
                    "default_code": product.default_code,
                    "uom_name": product.uom_id.name,
                    "list_price": product.list_price,
                }
            )

        return self._json_response({"data": data})

    # ---------------------------------------------------------------------
    # Cotizaciones desde la app del distribuidor
    # ---------------------------------------------------------------------
    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        """
        Crea una cotización (sale.order) en Odoo.

        Body esperado (JSON, ejemplo):
        {
            "partner_id": 123,           # Opcional. Si no viene se usa el partner del usuario API.
            "company_id": 1,             # Opcional. Si no viene se usa la compañía actual del usuario.
            "customer": {                # Opcional, se guarda a modo informativo en la nota del pedido.
                "name": "...",
                "phone": "...",
                "email": "...",
                "street": "...",
                "city": "..."
            },
            "notes": "texto libre desde la app",
            "external_reference": "código o referencia visible en la app",
            "lines": [
                {
                    "product_id": 10,
                    "quantity": 2
                }
            ]
        }
        """
        if request.httprequest.method == "OPTIONS":
            # Preflight CORS
            return self._json_response({}, status=200)

        env = request.env

        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response(
                {"error": "Invalid JSON payload."},
                status=400,
            )

        SaleOrder = env["sale.order"].sudo()
        Partner = env["res.partner"].sudo()
        Product = env["product.product"].sudo()
        Company = env["res.company"].sudo()

        # -------------------------------
        # Compañía
        # -------------------------------
        company = env.company
        company_id = payload.get("company_id")
        if company_id:
            try:
                company_id = int(company_id)
                company_candidate = Company.browse(company_id)
                if company_candidate and company_candidate.exists():
                    company = company_candidate
            except (TypeError, ValueError):
                pass

        # Aplicar compañía en el contexto
        SaleOrder = SaleOrder.with_context(force_company=company.id)
        Partner = Partner.with_context(force_company=company.id)
        Product = Product.with_context(force_company=company.id)

        # -------------------------------
        # Partner (cliente en Odoo)
        # -------------------------------
        partner_id = payload.get("partner_id")
        if partner_id:
            try:
                partner_id = int(partner_id)
            except (TypeError, ValueError):
                return self._json_response(
                    {"error": "partner_id must be an integer."},
                    status=400,
                )
            partner = Partner.browse(partner_id)
            if not partner.exists():
                return self._json_response(
                    {"error": "Partner not found."},
                    status=404,
                )
        else:
            # Usamos el partner del usuario (típicamente el distribuidor)
            partner = env.user.partner_id
            if not partner:
                return self._json_response(
                    {"error": "No partner specified and API user has no partner."},
                    status=400,
                )

        # -------------------------------
        # Líneas de pedido
        # -------------------------------
        lines_payload = payload.get("lines") or []
        if not isinstance(lines_payload, list) or not lines_payload:
            return self._json_response(
                {"error": "At least one order line is required."},
                status=400,
            )

        order_line_values = []
        for line in lines_payload:
            product_id = line.get("product_id")
            quantity = line.get("quantity") or line.get("qty")
            if not product_id or quantity is None:
                continue

            try:
                product_id = int(product_id)
                quantity = float(quantity)
            except (TypeError, ValueError):
                continue

            if quantity <= 0:
                continue

            product = Product.browse(product_id)
            if not product.exists():
                continue

            order_line_values.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": product.display_name,
                        "product_uom_qty": quantity,
                        "product_uom": product.uom_id.id,
                        # Por simplicidad usamos el precio de lista del producto.
                        # Si más adelante querés usar lista de precios, se ajusta acá.
                        "price_unit": product.list_price,
                    },
                )
            )

        if not order_line_values:
            return self._json_response(
                {"error": "No valid order lines found."},
                status=400,
            )

        # -------------------------------
        # Datos de cliente final / nota
        # -------------------------------
        customer = payload.get("customer") or {}
        notes = payload.get("notes") or ""
        customer_name = customer.get("name")
        customer_phone = customer.get("phone")
        customer_email = customer.get("email")
        customer_city = customer.get("city")
        customer_street = customer.get("street")

        note_lines = []
        if customer_name:
            note_lines.append(f"Cliente final: {customer_name}")
        if customer_phone:
            note_lines.append(f"Teléfono: {customer_phone}")
        if customer_email:
            note_lines.append(f"Email: {customer_email}")
        if customer_street or customer_city:
            note_lines.append(
                "Dirección: %s %s"
                % (customer_street or "", customer_city or "")
            )
        if notes:
            note_lines.append(f"Notas de la app: {notes}")

        order_vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "order_line": order_line_values,
        }

        external_reference = payload.get("external_reference")
        if external_reference:
            order_vals["client_order_ref"] = external_reference

        if note_lines:
            order_vals["note"] = "\n".join(note_lines)

        order = SaleOrder.create(order_vals)

        return self._json_response(
            {
                "success": True,
                "order_id": order.id,
                "name": order.name,
                "partner_id": order.partner_id.id,
                "company_id": order.company_id.id,
            }
        )
