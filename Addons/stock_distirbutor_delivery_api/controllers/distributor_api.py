
# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorApiController(http.Controller):
    """
    API para uso del presupuesto / entregas del distribuidor.

    Endpoints expuestos (todos con CORS simple y auth="public" + sudo):

    - GET/OPTIONS  /distributor/api/pickings
    - POST/OPTIONS /distributor/api/pickings/<id>/final_customer
    - GET/OPTIONS  /distributor/api/distributors
    - GET/OPTIONS  /distributor/api/products
    - POST/OPTIONS /distributor/api/quotations
    """

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _cors_headers(self):
        """Headers CORS básicos para la SPA del distribuidor."""
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

    def _json_response(self, payload, status=200):
        """Devuelve respuesta JSON con CORS siempre habilitado."""
        if not isinstance(payload, (str, bytes)):
            body = json.dumps(payload, default=str)
        else:
            body = payload

        headers = {
            "Content-Type": "application/json",
        }
        headers.update(self._cors_headers())

        response = request.make_response(body, headers=headers)
        response.status_code = status
        return response

    def _error(self, message, status=400, **extra):
        data = {"error": message}
        if extra:
            data["details"] = extra
        return self._json_response(data, status=status)

    def _get_json_body(self):
        """Parsea el body como JSON o devuelve {}."""
        raw = ""
        try:
            raw = request.httprequest.get_data().decode("utf-8") or ""
        except Exception:
            try:
                raw = (request.httprequest.data or b"").decode("utf-8")
            except Exception:
                raw = ""

        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            _logger.exception("No se pudo parsear JSON en %s", request.httprequest.path)
            raise

    def _get_vert_company(self):
        """Devuelve la compañía "Vert Deco Cercos" o, si no existe, la actual."""
        Company = request.env["res.company"].sudo()
        company = Company.search([("name", "=", "Vert Deco Cercos")], limit=1)
        if company:
            return company
        return request.env.company

    # -------------------------------------------------------------------------
    # Pickings pendientes de entrega
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        """Lista de entregas pendientes para distribuidor.

        Criterios:
        - picking_type_id.code = outgoing
        - state in (confirmed, assigned)
        - is_distributor_delivery = True
        - final_customer_completed = False
        """
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)

        user = request.env.user

        Picking = (
            request.env["stock.picking"]
            .sudo()
            .with_context(lang=user.lang)
        )

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
                    "is_distributor_delivery": picking.is_distributor_delivery,
                    "final_customer_completed": picking.final_customer_completed,
                    "final_customer_name": picking.final_customer_name,
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Final customer para picking
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """Guarda los datos del cliente final en el picking."""
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)

        picking = (
            request.env["stock.picking"]
            .sudo()
            .browse(picking_id)
        )
        if not picking.exists():
            return self._error("Picking no encontrado", status=404)

        data = self._get_json_body()

        picking.final_customer_name = data.get("name") or ""
        picking.final_customer_street = data.get("street") or ""
        picking.final_customer_city = data.get("city") or ""
        picking.final_customer_vat = data.get("vat") or ""
        picking.final_customer_phone = data.get("phone") or ""
        picking.final_customer_email = data.get("email") or ""
        picking.final_customer_notes = data.get("notes") or ""
        picking.final_customer_completed = True

        return self._json_response({"success": True})

    # -------------------------------------------------------------------------
    # Distribuidores (partners con etiqueta "Distribuidor")
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_distributors(self, **kwargs):
        """Devuelve los partners que actúan como distribuidores.

        Criterios:
        - customer_rank > 0
        - active = True
        - company_id in (False, Vert Deco)
        - categoría (etiqueta) "Distribuidor"
        """
        # Preflight
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)

        company = self._get_vert_company()

        Partner = (
            request.env["res.partner"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )

        domain = [
            ("customer_rank", ">", 0),
            ("active", "=", True),
            ("category_id.name", "=", "Distribuidor"),
            ("company_id", "in", [False, company.id]),
        ]

        partners = Partner.search(domain, order="name")

        data = []
        for partner in partners:
            data.append(
                {
                    "id": partner.id,
                    "name": partner.name,
                    "vat": partner.vat or "",
                    "street": partner.street or "",
                    "city": partner.city or "",
                    "phone": partner.phone or "",
                    "email": partner.email or "",
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Productos (Vert Deco + Lista Vip)
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """Lista de productos vendibles de Vert Deco con precio en Lista Vip."""
        # Preflight
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)

        company = self._get_vert_company()

        Pricelist = (
            request.env["product.pricelist"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )

        pricelist = Pricelist.search(
            [
                ("name", "=", "Lista Vip"),
                ("company_id", "in", [False, company.id]),
            ],
            limit=1,
        )
        if not pricelist:
            return self._error('No se encontró la lista de precios "Lista Vip".', status=404)

        Product = (
            request.env["product.product"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )

        domain = [
            ("sale_ok", "=", True),
            ("company_id", "in", [False, company.id]),
        ]
        products = Product.search(domain, order="default_code, name")

        data = []
        for product in products:
            try:
                prices = pricelist.price_get(product.id, 1.0, False) or {}
                price = prices.get(pricelist.id)
            except Exception:
                _logger.exception("Error calculando precio para producto %s", product.id)
                price = None

            # Solo productos con precio definido en Lista Vip
            if price is None:
                continue

            data.append(
                {
                    "id": product.id,
                    "name": product.display_name or product.name,
                    "default_code": product.default_code or "",
                    "uom_name": product.uom_id.name or "",
                    "price": price,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Crear presupuesto (sale.order) para Vert Deco + Lista Vip
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        """Crea un sale.order en Vert Deco Cercos a partir de líneas de productos.

        Body esperado (JSON):
        {
            "partner_id": <ID del distribuidor (res.partner)>,
            "client_reference": "Texto libre para referencia del cliente",
            "lines": [
                {"product_id": <ID product.product>, "quantity": <float>},
                ...
            ]
        }
        """
        # Preflight
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)

        data = self._get_json_body() or {}

        partner_id = data.get("partner_id")
        lines_data = data.get("lines") or []
        client_reference = data.get("client_reference") or ""

        if not partner_id:
            return self._error("Falta 'partner_id' (distribuidor).", status=400)
        if not lines_data:
            return self._error("No se recibió ninguna línea de producto.", status=400)

        company = self._get_vert_company()

        Partner = (
            request.env["res.partner"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )
        SaleOrder = (
            request.env["sale.order"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )
        Product = (
            request.env["product.product"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )
        Pricelist = (
            request.env["product.pricelist"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )

        partner = Partner.browse(partner_id)
        if not partner.exists():
            return self._error("Distribuidor no encontrado.", status=404)

        # Usamos la lista VIP siempre que exista, si no la propia del partner.
        vip_pricelist = Pricelist.search(
            [
                ("name", "=", "Lista Vip"),
                ("company_id", "in", [False, company.id]),
            ],
            limit=1,
        )
        pricelist = vip_pricelist or partner.property_product_pricelist

        order_line_commands = []

        for line in lines_data:
            product_id = line.get("product_id")
            qty = line.get("quantity") or 0.0

            try:
                qty = float(qty)
            except Exception:
                qty = 0.0

            if not product_id or qty <= 0:
                continue

            product = Product.browse(product_id)
            if not product.exists():
                continue

            price = 0.0
            if pricelist:
                try:
                    prices = pricelist.price_get(product.id, qty, partner) or {}
                    price = prices.get(pricelist.id, 0.0)
                except Exception:
                    _logger.exception(
                        "Error calculando precio en Lista Vip para producto %s", product.id
                    )
                    price = 0.0

            line_vals = {
                "product_id": product.id,
                "product_uom_qty": qty,
                "name": product.display_name or product.name,
            }
            if product.uom_id:
                line_vals["product_uom"] = product.uom_id.id
            if price:
                line_vals["price_unit"] = price

            order_line_commands.append((0, 0, line_vals))

        if not order_line_commands:
            return self._error("No hay líneas válidas para crear el presupuesto.", status=400)

        order_vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "order_line": order_line_commands,
        }
        if pricelist:
            order_vals["pricelist_id"] = pricelist.id
        if client_reference:
            order_vals["client_order_ref"] = client_reference

        order = SaleOrder.create(order_vals)

        return self._json_response(
            {
                "success": True,
                "order_id": order.id,
                "order_name": order.name,
            },
            status=200,
        )
