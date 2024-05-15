# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import io
import json
import time

import requests
from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    pitchprint_project_id = fields.Text(string="PP Project")

    def action_view_pp_design(self):
        # Open browser to first preview image in PP for current order line
        self.ensure_one()
        if not self.pitchprint_project_id:
            return False
        preview_url = (
            f"https://admin.pitchprint.com/projects#{self.pitchprint_project_id}"
        )
        action = {"type": "ir.actions.act_url", "target": "new", "url": preview_url}
        return action


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    custom_printdesign_count = fields.Integer(
        compute="_compute_custom_printdesign_count"
    )
    custom_printdesigns = fields.Text(
        compute="_compute_custom_printdesigns",
        store=True,
        string="PitchPrint Designs",
    )

    @api.depends("custom_printdesign_count", "order_line.pitchprint_project_id")
    def _compute_custom_printdesigns(self):
        for record in self:
            res = False
            designs = self.env["sale.order.line"].search(
                [("order_id", "=", record.id), ("pitchprint_project_id", "!=", False)]
            )
            if len(designs) > 0:
                res = designs.mapped("pitchprint_project_id")
            record.custom_printdesigns = res

    def _compute_custom_printdesign_count(self):
        for record in self:
            record.custom_printdesign_count = self.env["sale.order.line"].search_count(
                [("order_id", "=", record.id), ("pitchprint_project_id", "!=", False)]
            )

    def action_confirm(self):
        attachments = []
        for order in self:
            for ol in order.order_line:
                if ol.pitchprint_project_id:
                    # Force project service tracking if sale_projects is installed
                    if (
                        "project_template_id" in ol.product_id._fields
                        and ol.product_id.project_template_id
                    ):
                        ol.is_service = True
                    # Create path from PP URL
                    pdf_url = f"https://pdf.pitchprint.com/{ol.pitchprint_project_id}"
                    image_url = (
                        f"https://pitchprint.io/previews/{ol.pitchprint_project_id}_1.jpg"
                    )
                    try:
                        # CM-Test: Store project data to chatter as a JSON file
                        project_data = self.fetch_print_project(ol.pitchprint_project_id)
                        # Find page elements
                        pagedata_objects = self.find_page_data(json.loads(project_data))
                        # Construct new JSON object as string
                        new_json_data = self.construct_photos_json(pagedata_objects)
                        self.store_project_to_chatter(
                            new_json_data, ol.pitchprint_project_id
                        )

                        pdf_file = requests.get(pdf_url)
                        if (
                            pdf_file.status_code == 200
                            and pdf_file.headers["Content-Type"] == "application/pdf"
                        ):
                            # Download PDF from PitchPrint and store attachment + msg in chatter
                            attachment_id = self.env["ir.attachment"].create(
                                {
                                    "name": ol.pitchprint_project_id + ".pdf",
                                    "type": "binary",
                                    "datas": base64.b64encode(pdf_file.content),
                                    "store_fname": ol.pitchprint_project_id + ".pdf",
                                    "res_model": "sale.order",
                                    "res_id": self.id,
                                }
                            )
                            attachments.append(attachment_id.id)
                        image_file = requests.get(image_url)
                        if (
                            image_file.status_code == 200
                            and image_file.headers["Content-Type"] == "image/jpeg"
                        ):
                            # Download JPG from PitchPrint and store attachment + msg in chatter
                            attachment_id = self.env["ir.attachment"].create(
                                {
                                    "name": ol.pitchprint_project_id + ".jpg",
                                    "type": "binary",
                                    "datas": base64.b64encode(image_file.content),
                                    "store_fname": ol.pitchprint_project_id + ".jpg",
                                    "res_model": "sale.order",
                                    "res_id": self.id,
                                }
                            )
                            attachments.append(attachment_id.id)
                        else:
                            raise UserError(
                                _(
                                    "Error retrieving design images/PDF from PitchPrint, check Design ID."
                                )
                            )
                    except requests.exceptions.RequestException:
                        raise UserError(
                            _(
                                "Error whilst retrieving design images/PDF from PitchPrint, check connection and API key."
                            )
                        )
            # Post message in the chatter to all followers with attachment (mail.mt_note or mail.mt_comment)
            if order.custom_printdesign_count > 0:
                if order.env.su:
                    # sending mail in sudo was meant for it being sent from superuser
                    self = order.with_user(SUPERUSER_ID)
                mail_template = self.env.ref(
                    "ous_pitchprint_web2print.email_template_sales_order"
                )
                # V17 - Replaced message_post_with_template
                self.with_context(force_send=True).message_mail_with_source(
                    mail_template,
                    attachment_ids=attachments,
                    message_type="comment",
                    subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                        "mail.mt_comment"
                    ),
                )
        super(SaleOrderInherit, self).action_confirm()

    def web2print_cart_update(
        self,
        pitchprint_project_id,
        product_id,
        add_qty=0,
        set_qty=0,
        **kwargs,
    ):
        # Add a new unique line to cart per custom design with ref
        current_line = self.order_line.sudo().create(
            {
                "order_id": self.id,
                "product_uom_qty": int(add_qty),
                "product_id": int(product_id),
                "pitchprint_project_id": pitchprint_project_id,
            }
        )
        self._cart_update(
            line_id=int(current_line.id),
            product_id=int(product_id),
            add_qty=0,
            set_qty=0,
            **kwargs,
        )

    def fetch_print_project(self, project_id):
        url = "https://api.pitchprint.io/runtime/fetch-project"
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
        if not (project_id and api_key and secret_key):
            raise requests.exceptions.RequestException
        data = self._generate_signature(api_key, secret_key)
        data["projectId"] = project_id
        result = requests.post(url, json.dumps(data)).json()
        if not result.get("data", False):
            raise requests.exceptions.RequestException
        return json.dumps(result)

    def store_project_to_chatter(self, project_json, project_id):
        if not project_json:
            return
        formatted_json = json.dumps(json.loads(project_json), indent=4)
        file_obj = io.BytesIO()
        file_obj.write(formatted_json.encode())
        file_obj.seek(0)
        file_data_base64 = base64.b64encode(file_obj.getvalue())
        attachment_values = {
            "name": f"{project_id}.json",
            "res_model": self._name,
            "res_id": self.id,
            "datas": file_data_base64,
            "store_fname": f"{project_id}.json",
        }
        json_file = self.env["ir.attachment"].sudo().create(attachment_values)
        self.message_post(
            body="PitchPrint project photos data attached.",
            attachment_ids=[json_file.id],
        )

    def find_page_data(self, json_data, results=None):
        if results is None:
            results = []
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if key in ["pageData"]:
                    continue  # Skip superflous elements
                elif key in ["bookMark"]:
                    results.append(value)
                else:
                    self.find_page_data(value, results=results)
        elif isinstance(json_data, list):
            for item in json_data:
                self.find_page_data(item, results=results)
        return results

    def construct_photos_json(self, page_data_elements):
        if page_data_elements:
            return json.dumps({"photoPages": page_data_elements})

    def _generate_signature(self, api_key, secret_key):
        if api_key and secret_key:
            timestamp = str(int(round(time.time())))
            signature = hashlib.md5(
                (api_key + secret_key + timestamp).encode("utf-8")
            ).hexdigest()
            return {"timestamp": timestamp, "apiKey": api_key, "signature": signature}
        return False
