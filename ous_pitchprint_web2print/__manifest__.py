# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

{
    "name": "PitchPrint Web to Print",
    "version": "17.0.1.6.0",
    "category": "Website",
    "license": "OPL-1",
    "summary": "PitchPrint Web to Print integrated solution for designing custom e-Commerce products, from website to sale order.",
    "author": "Open User Systems",
    "website": "https://www.openusersystems.com",
    "price": 150,
    "currency": "EUR",
    "depends": ["website", "website_sale"],
    "data": [
        "security/pitchprint_security.xml",
        "views/product_template_inherit_views.xml",
        "views/product_inherit_views.xml",
        "views/sale_order_inherit_views.xml",
        "views/website_sale_inherit_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_design_views.xml",
        "views/pitchprint_menus.xml",
        "views/portal_templates.xml",
        "data/email_template_data.xml",
        "data/ir_cron_data.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
    "images": ["static/description/ous_pitchprint_web2print.png"],
    "assets": {
        "web.assets_frontend": [
            "ous_pitchprint_web2print/static/src/js/pitchprint_client.js",
        ]
    },
}
