# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError


class PresupuestadorPortalController(http.Controller):

    def _portal_domain(self):
        partner = request.env.user.partner_id
        return [("partner_id", "child_of", partner.id)]

    def _check_access_pedido(self, pedido):
        dom = self._portal_domain() + [("id", "=", pedido.id)]
        if not request.env["presupuestador.pedido"].sudo().search_count(dom):
            raise AccessError(_("No tiene permisos para acceder a este presupuesto."))

    @http.route(["/my/presupuestador"], type="http", auth="user", website=True)
    def portal_presupuestador_list(self, **kw):
        pedidos = request.env["presupuestador.pedido"].search(self._portal_domain(), order="create_date desc", limit=200)
        return request.render("dflex_presupuestador_portal.portal_presupuestador_list", {"pedidos": pedidos})

    @http.route(["/my/presupuestador/create"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_presupuestador_create(self, **post):
        website = request.website
        partner = request.env.user.partner_id
        pricelist = website.pricelist_id  # Idealmente: Predeterminado
        coef = float(post.get("coeficiente") or 25.0)

        pedido = request.env["presupuestador.pedido"].create({
            "partner_id": partner.id,
            "pricelist_id": pricelist.id,
            "coeficiente": coef,
        })
        return request.redirect(f"/my/presupuestador/{pedido.id}")

    @http.route(["/my/presupuestador/<int:pedido_id>"], type="http", auth="user", website=True)
    def portal_presupuestador_detail(self, pedido_id, **kw):
        pedido = request.env["presupuestador.pedido"].browse(pedido_id)
        if not pedido.exists():
            raise MissingError(_("Presupuesto inexistente."))
        self._check_access_pedido(pedido)

        rubros = request.env["presupuestador.rubro"].search([("active", "=", True)], order="sequence, name")
        products = request.env["product.product"].search([("sale_ok", "=", True)], limit=200)

        return request.render("dflex_presupuestador_portal.portal_presupuestador_detail", {
            "pedido": pedido,
            "rubros": rubros,
            "products": products,
        })

    @http.route(["/my/presupuestador/<int:pedido_id>/update_header"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_presupuestador_update_header(self, pedido_id, **post):
        pedido = request.env["presupuestador.pedido"].browse(pedido_id)
        if not pedido.exists():
            raise MissingError(_("Presupuesto inexistente."))
        self._check_access_pedido(pedido)

        vals = {}
        if "sistema" in post:
            vals["sistema"] = post.get("sistema") or False

        for f in ("coeficiente", "ancho", "alto", "peso_m2"):
            if f in post:
                try:
                    vals[f] = float(post.get(f) or 0.0)
                except Exception:
                    vals[f] = 0.0

        pedido.write(vals)
        if "coeficiente" in vals:
            pedido.line_ids.recompute_prices()

        return request.redirect(f"/my/presupuestador/{pedido.id}")

    @http.route(["/my/presupuestador/<int:pedido_id>/add_line"], type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def portal_presupuestador_add_line(self, pedido_id, **post):
        pedido = request.env["presupuestador.pedido"].browse(pedido_id)
        if not pedido.exists():
            raise MissingError(_("Presupuesto inexistente."))
        self._check_access_pedido(pedido)

        rubro_id = int(post.get("rubro_id"))
        product_id = int(post.get("product_id"))

        rubro = request.env["presupuestador.rubro"].browse(rubro_id)
        product = request.env["product.product"].browse(product_id)

        if rubro.qty_mode == "m2":
            qty = pedido.m2 or 0.0
        elif rubro.qty_mode == "one":
            qty = 1.0
        else:
            qty = float(post.get("qty") or 1.0)

        obs = post.get("obs") or False

        request.env["presupuestador.linea"].create({
            "pedido_id": pedido.id,
            "rubro_id": rubro.id,
            "product_id": product.id,
            "qty": qty,
            "obs": obs,
            "tax_ids": [(6, 0, product.taxes_id.filtered(lambda t: t.type_tax_use in ("sale", "none")).ids)],
        })

        return request.redirect(f"/my/presupuestador/{pedido.id}")

    @http.route(["/my/presupuestador/<int:pedido_id>/remove_line/<int:line_id>"], type="http", auth="user", website=True, csrf=True)
    def portal_presupuestador_remove_line(self, pedido_id, line_id, **kw):
        pedido = request.env["presupuestador.pedido"].browse(pedido_id)
        if not pedido.exists():
            raise MissingError(_("Presupuesto inexistente."))
        self._check_access_pedido(pedido)

        line = request.env["presupuestador.linea"].browse(line_id)
        if line.exists() and line.pedido_id.id == pedido.id:
            line.unlink()

        return request.redirect(f"/my/presupuestador/{pedido.id}")

    @http.route(["/my/presupuestador/<int:pedido_id>/print"], type="http", auth="user", website=True)
    def portal_presupuestador_print(self, pedido_id, **kw):
        pedido = request.env["presupuestador.pedido"].browse(pedido_id)
        if not pedido.exists():
            raise MissingError(_("Presupuesto inexistente."))
        self._check_access_pedido(pedido)

        report = request.env.ref("dflex_presupuestador_portal.action_report_presupuestador_pedido")
        pdf, _ = report._render_qweb_pdf([pedido.id])
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", str(len(pdf))),
            ("Content-Disposition", f'inline; filename="Presupuesto_{pedido.name}.pdf"'),
        ]
        return request.make_response(pdf, headers=headers)
