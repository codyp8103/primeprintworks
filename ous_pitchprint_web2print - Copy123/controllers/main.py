# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSalePrintDesign(WebsiteSale):
    @http.route(
        ["/shop/cart/update_json"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_update_json(self, *args, product_id, line_id=None, add_qty=None, **kwargs):
        # If custom print design product is newly added to cart force new sale order line
        order = request.website.sale_get_order(force_create=True)
        new_design_project = self.retrieve_print_design()
        if new_design_project and (add_qty and int(add_qty) > 0) and not line_id:
            for variation_design in new_design_project:
                order.web2print_cart_update(
                    pitchprint_project_id=variation_design,
                    product_id=product_id,
                    add_qty=add_qty,
                    **kwargs,
                )
            request.session.pop("pitchprint_project")
            add_qty = 0
        return super(WebsiteSalePrintDesign, self).cart_update_json(
            *args, product_id=product_id, line_id=line_id, add_qty=add_qty, **kwargs
        )

    @http.route(
        ["/shop/cart/update"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_update(self, *args, product_id, add_qty=1, set_qty=0, **kwargs):
        # If custom print design product is newly added to cart force new sale order line\
        order = request.website.sale_get_order(force_create=True)
        new_design_project = self.retrieve_print_design()
        if new_design_project and (add_qty and int(add_qty) > 0):
            for variation_design in new_design_project:
                order.web2print_cart_update(
                    pitchprint_project_id=variation_design,
                    product_id=product_id,
                    add_qty=add_qty,
                    **kwargs,
                )
            request.session.pop("pitchprint_project")
            add_qty = 0
            set_qty = 0
        return super(WebsiteSalePrintDesign, self).cart_update(
            *args, product_id=product_id, add_qty=add_qty, set_qty=set_qty, **kwargs
        )

    @http.route(
        ["/shop/product/getdesign"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def get_product_design(self, product_id, **kwargs):
        rec = False
        design = []
        prod = request.env["product.product"].search([("id", "=", product_id)])
        if prod:
            design = request.env["product.design"].search(
                [("id", "=", prod.pitchprint_design_id.id)]
            )
        if design:
            rec = design.design_id
        return rec

    @http.route(
        ["/shop/product/storedesign"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def store_product_design(self, id, product_id, variations_count):
        if id:
            request.session["pitchprint_project"] = {
                "id": id,
                "product_id": product_id,
                "variations_count": variations_count,
            }
        return {"success": True}

    def retrieve_print_design(self):
        res = []
        if "pitchprint_project" in request.session:
            pitchprint_project = request.session["pitchprint_project"]
            # Retrieve variations count (is variable module used in PP)
            if pitchprint_project["variations_count"]:
                variations = int(pitchprint_project["variations_count"])
                for variation in range(0, variations):
                    res.append(pitchprint_project["id"] + "_vd_" + str(variation))
            else:
                res = [pitchprint_project["id"]]
        return res

    # User controlled feature to require login before being able to checkout
    @http.route(
        ["/shop/checkout"], type="http", auth="public", website=True, sitemap=False
    )
    def checkout(self, **post):
        require_login_to_checkout = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("ous_pitchprint_web2print.login_checkout")
        )
        public_user = request.env.user == request.website.user_id
        express = post.get("express") or str(0)
        if public_user and require_login_to_checkout:
            return request.redirect(
                "/web/login?redirect=/shop/checkout?express=" + express, code=302
            )
        else:
            return super().checkout(**post)
