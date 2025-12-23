# -*- coding: utf-8 -*-
import json
import logging

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorController(http.Controller):
    """API para app de distribuidores"""

    # ========================
    # Helpers
    # ========================

    def _add_cors_headers(self, response):
        """Agrega encabezados CORS a cualquier respuesta."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers[
            "Access-Control-Allow-Headers"
        ] = "Origin, X-Requested-With, Content-Type, Accept, Authorization"
        return response

    def _json_response(self, data, status=200):
        """Respuesta JSON con CORS."""
        body = json.dumps(data, default=str)
        response = request.make_response(
            body,
            headers=[("Content-Type", "application/json")],
        )
        response.status_code = status
        return self._add_cors_headers(response)

    def _get_vert_company(self):
        """Devuelve la compañía Vert Deco Cercos; fallback a la compañía actual."""
        Company = request.env["res.company"].sudo()
        company = Company.search([("name", "ilike", "Vert Deco Cercos")], limit=1)
        if not company:
            company = request.env.company
        return company

    def _get_distributor_partners(self, company):
        """Devuelve los partners marcados con etiqueta 'Distribuidor' en esa compañía."""
        Partner = request.env["res.partner"].sudo().with_company(company)
        distributors = Partner.search(
            [
                ("company_id", "=", company.id),
                ("category_id.name", "=", "Distribuidor"),
                ("customer_rank", ">", 0),
            ]
        )
        return distributors

    # ========================
    # Pickings para entregas
    # ========================

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="user",
        csrf=False,
        methods=["GET", "OPTIONS"],
    )
    def list_pickings(self, **kwargs):
        """Listado de remitos pendientes de entrega vía distribuidor."""
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            resp = request.make_response("")
            return self._add_cors_headers(resp)

        env = request.env
        StockPicking = env["stock.picking"].sudo()

        domain = [
            ("picking_type_code", "=", "outgoing"),
            ("state", "in", ["assigned", "confirmed", "waiting", "ready"]),
            ("distributor_delivery", "=", True),
        ]

        pickings = StockPicking.search(
            domain,
            order="scheduled_date asc, id asc",
            limit=200,
        )

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
                    "partner_id": picking.partner_id.id,
                    "partner_name": picking.partner_id.display_name,
                    "scheduled_date": picking.scheduled_date
                    and fields.Datetime.to_string(picking.scheduled_date)
                    or False,
                    "state": picking.state,
                    "final_customer_completed": bool(picking.final_customer_name),
                    "final_customer_name": picking.final_customer_name or False,
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="user",
        csrf=False,
        methods=["POST", "OPTIONS"],
    )
    def set_final_customer(self, picking_id, **kwargs):
        """Guardar datos de cliente final en el picking."""
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            resp = request.make_response("")
            return self._add_cors_headers(resp)

        try:
            payload = request.get_json_data()
        except Exception:
            payload = {}

        name = (payload.get("name") or "").strip()
        street = (payload.get("street") or "").strip()
        city = (payload.get("city") or "").strip()
        vat = (payload.get("vat") or "").strip()
        phone = (payload.get("phone") or "").strip()
        email = (payload.get("email") or "").strip()
        notes = (payload.get("notes") or "").strip()

        if not name or not street:
            return self._json_response(
                {"error": "Nombre y calle/dirección son obligatorios."},
                status=400,
            )

        env = request.env
        StockPicking = env["stock.picking"].sudo()
        picking = StockPicking.browse(picking_id)
        if not picking.exists():
            return self._json_response(
                {"error": "Picking no encontrado."},
                status=404,
            )

        picking.write(
            {
                "final_customer_name": name,
                "final_customer_street": street,
                "final_customer_city": city,
                "final_customer_vat": vat,
                "final_customer_phone": phone,
                "final_customer_email": email,
                "final_customer_notes": notes,
            }
        )

        return self._json_response({"result": "ok"})

    # ========================
    # Distribuidores (clientes)
    # ========================

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="user",
        csrf=False,
        methods=["GET", "OPTIONS"],
    )
    def list_distributors(self, **kwargs):
        """
        Devuelve los clientes con etiqueta 'Distribuidor'
        de la empresa Vert Deco Cercos.
        """
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            resp = request.make_response("")
            return self._add_cors_headers(resp)

        company = self._get_vert_company()
        distributors = self._get_distributor_partners(company)

        data = [
            {
                "id": p.id,
                "name": p.display_name,
                "vat": p.vat,
            }
            for p in distributors
        ]

        return self._json_response({"data": data})

    # ========================
    # Productos (Vert Deco + Lista Vip)
    # ========================

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="user",
        csrf=False,
        methods=["GET", "OPTIONS"],
    )
    def list_products(self, **kwargs):
        """
        Devuelve los productos vendibles de Vert Deco Cercos que tengan
        precio en la lista de precios 'Lista Vip'.

        Respuesta:
            data: [
                {
                    "id": int,
                    "name": str,
                    "default_code": str | False,
                    "uom_name": str,
                    "price": float,
                },
                ...
            ]
        """
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            resp = request.make_response("")
            return self._add_cors_headers(resp)

        company = self._get_vert_company()

        Product = request.env["product.product"].with_company(company).sudo()
        Pricelist = request.env["product.pricelist"].with_company(company).sudo()

        # Buscar la lista 'Lista Vip' de Vert Deco
        pricelist = Pricelist.search(
            [("name", "=", "Lista Vip"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not pricelist:
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
                # price_get devuelve {pricelist_id: price}
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

    # ========================
    # Crear cotización en Vert Deco
    # ========================

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="user",
        csrf=False,
        methods=["POST", "OPTIONS"],
    )
    def create_quotation(self, **kwargs):
        """
        Crea una cotización (sale.order) en la empresa Vert Deco Cercos
        usando la lista 'Lista Vip', para un distribuidor marcado en Odoo.
        Espera un payload JSON del estilo:

        {
          "distributor_id": <partner_id>,
          "lines": [
            { "product_id": <id>, "quantity": 2 },
            ...
          ]
        }
        """
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            resp = request.make_response("")
            return self._add_cors_headers(resp)

        try:
            payload = request.get_json_data()
        except Exception:
            payload = {}

        distributor_id = payload.get("distributor_id")
        lines = payload.get("lines") or []

        if not distributor_id:
            return self._json_response(
                {"error": "Falta el distribuidor."},
                status=400,
            )
        if not lines:
            return self._json_response(
                {"error": "No hay líneas de productos."},
                status=400,
            )

        company = self._get_vert_company()
        env = request.env

        Partner = env["res.partner"].sudo().with_company(company)
        SaleOrder = env["sale.order"].sudo().with_company(company)
        Product = env["product.product"].sudo().with_company(company)
        Pricelist = env["product.pricelist"].sudo().with_company(company)

        partner = Partner.browse(distributor_id)
        if not partner.exists():
            return self._json_response(
                {"error": "Distribuidor no encontrado."},
                status=404,
            )

        pricelist = Pricelist.search(
            [("name", "=", "Lista Vip"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not pricelist:
            return self._json_response(
                {"error": "No se encontró la lista de precios 'Lista Vip'."},
                status=400,
            )

        # Crear la orden de venta en estado borrador
        order_vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "pricelist_id": pricelist.id,
            "state": "draft",
            "origin": "App Distribuidor",
        }
        order = SaleOrder.create(order_vals)

        order_lines_vals = []

        for line in lines:
            product_id = line.get("product_id")
            quantity = line.get("quantity") or 0.0

            if not product_id or quantity <= 0:
                continue

            product = Product.browse(product_id)
            if not product.exists():
                continue

            # Precio desde la lista Vip
            try:
                res = pricelist.price_get(product.id, quantity, partner.id)
                price = res.get(pricelist.id) or 0.0
            except Exception:
                price = 0.0

            order_lines_vals.append(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "product_uom_qty": quantity,
                    "name": product.get_product_multiline_description_sale()
                    or product.display_name,
                    "price_unit": price,
                }
            )

        if order_lines_vals:
            env["sale.order.line"].sudo().create(order_lines_vals)
        else:
            # Si no hay líneas válidas, borrar el pedido y devolver error
            order.unlink()
            return self._json_response(
                {"error": "No se pudieron crear líneas de pedido válidas."},
                status=400,
            )

        return self._json_response(
            {
                "result": "ok",
                "order_id": order.id,
                "order_name": order.name,
                "state": order.state,
            },
            status=201,
        )
