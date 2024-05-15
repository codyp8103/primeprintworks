# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

import base64
import datetime
import hashlib
import json
import time

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductDesign(models.Model):
    _name = "product.design"
    _description = "Product Design"
    _order = "sequence"

    _sql_constraints = [
        ("unique_design_id", "UNIQUE(design_id)", "The Design ID must be unique.")
    ]

    active = fields.Boolean(default=True)
    name = fields.Char("Title", required=True)
    category_id = fields.Char("Category")
    design_id = fields.Char("Design ID")
    lastModified = fields.Datetime("Last Modified")
    unit = fields.Char(size=10)
    previews = fields.Text()
    image = fields.Binary()
    variant_id = fields.One2many(
        "product.product", "variant_design_id", string="Variants"
    )
    product_id = fields.One2many(
        "product.template", "pitchprint_design_id", string="Products"
    )
    variant_count = fields.Integer(compute="_compute_variant_count")
    product_count = fields.Integer(compute="_compute_product_count")
    sequence = fields.Integer()

    def _compute_variant_count(self):
        for record in self:
            record.variant_count = self.env["product.product"].search_count(
                [("variant_design_id", "=", record.id)]
            )

    def _compute_product_count(self):
        for record in self:
            record.product_count = self.env["product.template"].search_count(
                [("pitchprint_design_id", "=", record.id)]
            )

    def get_products(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Products",
            "view_mode": "tree",
            "res_model": "product.template",
            "domain": [("pitchprint_design_id", "=", self.id)],
            "context": "{'create': False}",
        }

    def get_variants(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Product Variants",
            "view_mode": "tree",
            "res_model": "product.product",
            "domain": [("variant_design_id", "=", self.id)],
            "context": "{'create': False}",
        }

    def fetch_designs(self, user_mode=False):
        try:
            sequence = 0
            url = "https://api.pitchprint.io/runtime/fetch-designs"
            api_key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("ous_pitchprint_web2print.api_key")
            )
            secret_key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("ous_pitchprint_web2print.secret_key")
            )
            if not api_key or not secret_key:
                raise requests.exceptions.RequestException
            data = self._generate_signature(api_key, secret_key)
            response = requests.post(url, json.dumps(data))
            result = response.json()
            if not result.get("data", False):
                raise requests.exceptions.RequestException
            # Archive all existing designs
            self.env["product.design"].search([]).write({"active": False})
            # Get all live designs and update or create as needed
            for c in result["data"]:
                # Create category as a design with * appended to ID
                found = (
                    self.env["product.design"]
                    .with_context(active_test=False)
                    .search([("design_id", "=", "*" + c["id"])], limit=1)
                )
                vals = {
                    "name": "#" + c["title"].upper(),
                    "category_id": c["title"],
                    "design_id": "*" + c["id"],
                    "lastModified": datetime.datetime.fromtimestamp(c["created"]),
                    "sequence": sequence,
                }
                sequence += 1
                if found:
                    found.write({"active": True})
                    if vals["lastModified"] > found.lastModified:
                        found.write(vals)
                else:
                    self.env["product.design"].create(vals)
                # Create designs
                for d in c["items"]:
                    d["category"] = c["title"]
                    found = (
                        self.env["product.design"]
                        .with_context(active_test=False)
                        .search([("design_id", "=", d["id"])], limit=1)
                    )
                    image = base64.b64encode(requests.get(d["previews"][0]).content)
                    vals = {
                        "name": d["title"],
                        "category_id": d["category"],
                        "design_id": d["id"],
                        "lastModified": datetime.datetime.fromtimestamp(
                            d["lastModified"]
                        ),
                        "unit": d["unit"],
                        "previews": d["previews"],
                        "image": image,
                        "sequence": sequence,
                    }
                    sequence += 1
                    if found:
                        found.write({"active": True})
                        if vals["lastModified"] > found.lastModified:
                            found.write(vals)
                    else:
                        self.env["product.design"].create(vals)
        except requests.exceptions.RequestException:
            if user_mode:
                raise UserError(
                    _(
                        "Error while fetching product designs from PitchPrint. Check API Key and Secret Key."
                    )
                )
        return result

    def _generate_signature(self, api_key, secret_key):
        if api_key and secret_key:
            timestamp = str(int(round(time.time())))
            signature = hashlib.md5(
                str(api_key + secret_key + timestamp).encode("utf-8")
            ).hexdigest()
            result = {"timestamp": timestamp, "apiKey": api_key, "signature": signature}
        else:
            result = False
        return result

    # V17 - Replaced name_get
    def _compute_display_name(self):
        for record in self:
            name = "%s (%s)" % (record.name, record.category_id)
            record.display_name = name

    # V17 - Replaced name_search
    @api.model
    def _name_search(
        self, name="", domain=None, operator="ilike", limit=None, order=None
    ):
        domain = domain or []
        if name:
            domain = [
                "|",
                "|",
                ("name", operator, name),
                ("design_id", operator, name),
                ("category_id", operator, name),
            ] + domain
        return super(ProductDesign, self)._search(
            domain,
            limit=limit,
            order=order,
        )
