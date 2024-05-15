# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.website.tools import MockRequest
from odoo.tests.common import TransactionCase

from ..controllers.main import WebsiteSalePrintDesign

_logger = logging.getLogger(__name__)


class TestPitchPrintProduct(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.website = self.env["website"].browse(1)
        self.WebsiteSaleController = WebsiteSalePrintDesign()
        self.public_user = self.env.ref("base.public_user")
        self.pp_project_id = "835a460c916dec74f02adef0e4a9dce9"
        _logger.info("**PP: CREATE PRODUCT_DESIGN**")
        self.product_design = self.env["product.design"].create(
            {
                "name": "Business Card",
                "category_id": "Stationery",
                "design_id": "483b2844dc4a72003728989178d8d387",
                "unit": "cm",
            }
        )
        _logger.info("**PP: CREATE PRODUCT**")
        self.product = self.env["product.template"].create(
            {
                "name": "Business Card",
                "detailed_type": "consu",
                "is_pitchprint_design": True,
                "pitchprint_design_id": self.product_design.id,
                "is_published": True,
            }
        )

    def test_product_create(self):
        website = self.website.with_user(self.public_user)
        so = False
        self.assertEqual(self.product_design.active, True)
        self.assertEqual(self.product.active, True)
        with MockRequest(
            self.product.with_user(self.public_user).env,
            website=self.website.with_user(self.public_user),
        ):
            # Store custom design to product
            _logger.info("**PP: STORED CUSTOM DESIGN TO PRODUCT ON WEBSITE**")
            self.WebsiteSaleController.store_product_design(
                id=self.pp_project_id,
                product_id=self.product.product_variant_id.id,
                variations_count=0,
            )
            # Add to cart with design
            _logger.info("**PP: ADDED TO CART ON WEBSITE**")
            self.WebsiteSaleController.cart_update_json(
                product_id=self.product.product_variant_id.id, add_qty=1
            )
            so = website.sale_get_order(force_create=True)
            # Inspect resulting SO
            for line in so.order_line:
                self.assertEqual(line.pitchprint_project_id, self.pp_project_id)
            # so.action_confirm()
            # pdf = so.message_main_attachment_id
            # _logger.info("**PP: PDF DOWNLOADED " + pdf.name)
        _logger.info("**PP: S.O CREATED SUCCESSFULLY: " + str(so.name) + " **")
