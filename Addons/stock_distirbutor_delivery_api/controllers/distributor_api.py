# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class DistributorApiController(http.Controller):
    """
    API para app de distribuidor:
    - Pickings pendientes de entrega (con datos de cliente final).
    - Catálogo de productos para presupuestar (solo Vert Deco Cercos).
    - Lista de distribuidores (partners con etiqueta 'Distribuidor').
    - Creación de cotizaciones desde la app.
    """

    # ---------- Helpers ----------

    def _json_response(self, data, status=200):
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

    def _get_vert_company(self):
        """Devuelve la compañía 'Vert Deco Cercos' si existe, sino la compañía actual."""
        Company = request.env["res.company"].sudo()
        company = Company.search([("name", "=", "Vert Deco Cercos")], limit=1)
        if not company:
            company = request.env.company
        return company

    # ---------- Pickings para entrega ----------

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
            return self._json_response({}, status=200)

        # Parsear JSON del body
        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response(
                {"error": "Invalid JSON payload."},
                status=400,
            )

        Picking = request.env["stock.picking"].sudo()

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

    # ---------- Distribuidores (partners con etiqueta) ----------

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_distributors(self, **kwargs):
        """
        Devuelve una lista de distribuidores para el presupuestador.

        Selecciona res.partner que:
        - Tengan la etiqueta (categoria_id) con nombre que contenga 'Distribuidor'
        - Sean clientes (customer_rank > 0)
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user
        Partner = request.env["res.partner"].sudo().with_context(lang=user.lang)

        domain = [
            ("category_id.name", "ilike", "Distribuidor"),
            ("customer_rank", ">", 0),
            ("active", "=", True),
        ]

        partners = Partner.search(domain, order="name")

        data = [
            {
                "id": p.id,
                "name": p.name,
                "vat": p.vat,
                "ref": p.ref,
                "email": p.email,
                "phone": p.phone,
            }
            for p in partners
        ]

        return self._json_response({"data": data})

    # ---------- Productos (solo Vert Deco Cercos) ----------

        # ---------- Productos para presupuestador (Vert Deco + Lista Vip) ----------
    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """
        Devuelve los productos vendibles de Vert Deco Cercos que tengan
        precio en la lista de precios 'Lista Vip'.

        La respuesta incluye:
            - id: ID de product.product
            - name: nombre a mostrar
            - default_code: referencia interna
            - uom_name: unidad de medida
            - price: precio según Lista Vip
        """
        # CORS preflight
        if request.httprequest.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, Authorization",
            }
            return request.make_response("", headers=headers)

        company = self._get_vert_company()

        Product = request.env["product.product"].with_company(company).sudo()
        Pricelist = request.env["product.pricelist"].with_company(company).sudo()

        # Buscar la lista 'Lista Vip' de Vert Deco
        pricelist = Pricelist.search(
            [("name", "=", "Lista Vip"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not pricelist:
            # Si no existe, devolvemos vacío y mensaje
            return self._json_response(
                {
                    "data": [],
                    "message": "No se encontró la lista de precios 'Lista Vip' para Vert Deco Cercos.",
                }
            )

        # Productos vendibles de Vert Deco (o compartidos sin compañía)
        domain = [
            ("sale_ok", "=", True),
            ("company_id", "in", [False, company.id]),
        ]

        products = Product.search(domain)

        data = []

        for p in products:
            price = None
            try:
                # price_get devuelve un dict {pricelist_id: precio}
                res = pricelist.price_get(p.id, 1.0, False)
                price = res.get(pricelist.id)
            except Exception:
                price = None

            # Saltar productos sin precio en la lista
            if price in (None, False):
                continue

            data.append(
                {
                    "id": p.id,
                    "name": p.display_name,
                    "default_code": p.default_code,
                    "uom_name": p.uom_id.name,
                    "price": price,
                }
            )

        return self._json_response({"data": data})

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

        Body esperado (JSON):
        {
            "partner_id": <ID del distribuidor (res.partner)>,
            "client_reference": "...",   // opcional
            "lines": [
                {"product_id": <ID product.product>, "quantity": 2},
                ...
            ]
        }
        """
        if request.httprequest.method == "OPTIONS":
            # Preflight: permitir POST desde el front
            return self._json_response({}, status=200)

        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response(
                {"error": "Invalid JSON payload."},
                status=400,
            )

        partner_id = payload.get("partner_id")
        lines = payload.get("lines") or []
        client_ref = payload.get("client_reference")

        if not partner_id or not isinstance(lines, list) or not lines:
            return self._json_response(
                {"error": "partner_id y al menos una línea son obligatorios."},
                status=400,
            )

        company = self._get_vert_company()

        Partner = request.env["res.partner"].sudo().with_company(company)
        partner = Partner.browse(partner_id).exists()
        if not partner:
            return self._json_response(
                {"error": "Distribuidor no encontrado."},
                status=404,
            )

        SaleOrder = (
            request.env["sale.order"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id], company_id=company.id)
        )
        Product = (
            request.env["product.product"]
            .sudo()
            .with_company(company)
            .with_context(allowed_company_ids=[company.id])
        )

        order_line_commands = []
        for line in lines:
            product_id = line.get("product_id")
            qty = line.get("quantity") or 0.0
            try:
                qty = float(qty)
            except Exception:
                qty = 0.0

            if not product_id or qty <= 0:
                continue

            product = Product.browse(product_id).exists()
            if not product:
                continue

            order_line_commands.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": qty,
                    },
                )
            )

        if not order_line_commands:
            return self._json_response(
                {"error": "No se pudieron crear líneas de pedido válidas."},
                status=400,
            )

        vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "order_line": order_line_commands,
        }

        if client_ref:
            vals["client_order_ref"] = client_ref

        # Tomar la lista de precios del partner si existe
        if partner.property_product_pricelist:
            vals["pricelist_id"] = partner.property_product_pricelist.id

        order = SaleOrder.create(vals)

        return self._json_response(
            {
                "success": True,
                "order_id": order.id,
                "name": order.name,
            },
            status=201,
        )
