/** @odoo-module **/

//V17 onwards
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
import Dialog from "@web/legacy/js/core/dialog";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
//Pre-V17
// odoo.define('ous_pitchprint_web2print.pitchprint_client', function (require) {
//     'use strict';

//     var ajax = require('web.ajax');
//     var publicWidget = require('web.public.widget');
//     var VariantMixin = require('sale.VariantMixin');
//     var core = require('web.core');
//     var Dialog = require('web.Dialog');
//     var session = require('web.session');
//     var _t = core._t;

//Init PitchPrint Client
var ppClient = null;
const debugMode = false;

//Retrieve product design from PP, show carousel of preview images
const displayCustomDesigns = (pid, threeData = null) => {
    let printDesign = localStorage.getItem("pp" + pid);
    let storedImages = localStorage.getItem("pp" + pid + "img");
    let div = document.createElement("div");
    let carousel = document.getElementById("o-carousel-product");
    if (storedImages !== null && printDesign !== null) {
        //Render 3D
        if (threeData !== null && threeData != "false") {
            let iframe = document.createElement('iframe');
            carousel.innerHTML = '';
            iframe = document.createElement('iframe');
            iframe.src = `https://pitchprint.io/3d/index.html?vars=${encodeURIComponent(threeData)}`;
            iframe.style.width = '100%';
            iframe.style.height = '400px';
            iframe.style.border = 'none';
            iframe.style['z-index'] = '99999';
            carousel.appendChild(iframe);
        }
        else {
            if (debugMode) console.log("Display custom design: " + printDesign);
            //Split image string
            storedImages = storedImages.split(",");
            //Create carousel
            div.innerHTML = `
            <div id="o-carousel-product" class="carousel slide position-sticky mb-3 overflow-hidden" data-ride="carousel" data-interval="0" data-bs-ride="carousel" data-bs-interval="0" data-name="Product Carousel" style="top: 61px;">
            <div class="o_carousel_product_outer carousel-outer position-relative flex-grow-1" style="background:#F8F9FA">
            <div class="carousel-inner h-100">
            </div>
            <a class="carousel-control-prev" href="#o-carousel-product" role="button" data-slide="prev" data-bs-slide="prev">
            <span class="fa fa-chevron-left fa-2x oe_unmovable" role="img" aria-label="Previous" title="Previous"></span>
            </a>
            <a class="carousel-control-next" href="#o-carousel-product" role="button" data-slide="next" data-bs-slide="next">
            <span class="fa fa-chevron-right fa-2x oe_unmovable" role="img" aria-label="Next" title="Next"></span>
            </a>
            </div>
            <div class="o_carousel_product_indicators pt-2 overflow-hidden">
            <ol class="carousel-indicators position-static pt-2 pt-lg-0 mx-auto my-0 text-left text-start" style="justify-content: center;">
            </ol>
            </div>
            </div>
            `;
            //Replace standard Odoo carousel div
            if (carousel != null)
                carousel.replaceWith(div);
            //Loop through images and store to carousel
            for (var i = 0; i < storedImages.length; i++) {
                $(`<div class="carousel-item h-100" style="min-height:400px;"><div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="${storedImages[i]}?t=${new Date().getTime()}" class="img img-fluid oe_unmovable product_detail_img mh-100" loading="lazy"></div></div>`).appendTo('.carousel-inner');
                //Conditionally display carousel indicators only when > 1 preview image. Reformat to be box with number inside instead of black rectangle.
                if (storedImages.length > 1) {
                    $(`<li style="margin-bottom:3px;border-radius:0;padding:0px;max-height:24px;max-width:24px;text-align:center;" data-target="#o-carousel-product" data-slide-to="${i}" data-bs-target="#o-carousel-product" data-bs-slide-to="${i}" title="${i + 1} of ${storedImages.length}">${i + 1}</li>`).appendTo('.carousel-indicators');
                }
            }
            $(".carousel-item").first().addClass("active");
            $(".carousel-indicators > li").first().addClass("active");
            $("#o-carousel-product").carousel();
        }
        //Show the [Add to Cart] button
        toggleAddToCartButton(true);
    }
};

//Change the PP product background template image colour to match
//selected option on Odoo product attributes
const changeTemplateColour = () => {
    let colours = $("label.css_attribute_color > input");
    let colour_current = colours.filter(':checked');
    let colour_id = colour_current.index("label.css_attribute_color > input");
    if (colours != null) {
        ppClient.fire('change-color-template', colour_id);
    }
};

const toggleLoader = (show = false) => {
    //Show hide the spinner loader
    let loaderDiv = document.getElementById('pp_loader_div');
    if (show) {
        loaderDiv.style.display = 'inline-block';
    }
    else {
        loaderDiv.style.display = 'none';
    }
}

const toggleCustomiseButtons = (show = false) => {
    //Show / Hide the Customise and Reset buttons for custom products
    let launchButton = document.getElementById('launch_btn');
    let resetBtn = document.getElementById('reset_btn');
    try {
        if (show) {
            launchButton.style.display = "inline-block";
            resetBtn.style.display = "inline-block";
        }
        else {
            launchButton.style.display = "none";
            resetBtn.style.display = "none";
        }
    } catch (err) { }
};

const toggleAddToCartButton = (show = false) => {
    let addToCartBtn = document.getElementById('add_to_cart');
    if (show) {
        //Show the [Add to Cart] button
        if (addToCartBtn !== null) addToCartBtn.style.display = "inline-block";
    }
    else {
        //Hide the [Add to Cart] button
        if (addToCartBtn !== null) addToCartBtn.style.cssText = "display:none !important";
    };
}

//Function to run once the app is validated (ready to be used)
const appValidated = () => {
    if (debugMode) console.log("PP appValidated");
    let launchButton = document.getElementById('launch_btn');
    let resetBtn = document.getElementById('reset_btn');
    resetBtn.onclick = () => reset();
    launchButton.onclick = () => ppClient.showApp();;		//Attach event listener to the button when clicked to show the app
    toggleLoader(false);
};

//Function to run once the user has saved their project
const projectSaved = (_val) => {
    var _data = _val.data;
    if (_data && _data.previews && _data.previews.length) {
        if (debugMode) console.log("Saving design with product ID: " + ppProductId);
        //Store variations if present (variable data module)
        if (_data.variation) {
            localStorage.setItem("pp" + ppProductId + "vd", _data.variation.length);
        }
        localStorage.setItem("pp" + ppProductId, _data.projectId);
        localStorage.setItem("pp" + ppProductId + "img", _data.previews);
        displayCustomDesigns(ppProductId, JSON.stringify(_data.source.threeData));
    }
};

// //Reset button clicked, clear current print design and refresh page
const reset = () => {
    Dialog.confirm(
        this,
        _t("Reset ALL custom print designs to default?"),
        {
            onForceClose: function () {
                //Closed
            },
            confirm_callback: function () {
                //Confirmed
                localStorage.clear();
                location.reload(true);
            },
            cancel_callback: function () {
                //Cancelled
            }
        }
    );
};

//When design loaded, change colour of PP background template selected
//Note: mapping between the 0 based index of colour in PP to Odoo attributes needed.
const designLoaded = () => {
    if (debugMode) console.log("DesignLoaded event fired");
    changeTemplateColour();
};

//When template colour changed in PP interface, force it to reset
//to match the one provided by Odoo product attribute preference to prevent mismatch.
const templateColourChanged = () => {
    changeTemplateColour();
    ppClient.fire('do-reload');
    //Display warning message that colour preference must be chosen on Odoo shop
    ppClient.fire('show-flash', {
        text: _t('Change colour in shop'),
        icon: 'icon-text_fields',
        delay: 3000
    });
};

// This function returns a promise that resolves to the server version
function getServerVersion() {
    return session.rpc("/web/webclient/version_info", {}).then((result) => {
        return parseFloat(result.server_serie);
    });
};

var editorShown = () => {
    //PP client editor is visible - Force reload design/project
    var printDesign = localStorage.getItem("pp" + ppProductId);
    if (debugMode) console.log("PP Editor shown");
    if (printDesign != null) {
        if (debugMode) console.log("PP Editor shown - project loaded: " + printDesign);
        ppClient.fire('load-project-by-id', printDesign);
    }
    else {
        ppClient.fire('load-design-by-id', ppDesignId);
        ppClient.fire('do-reload-design');
    }
}

publicWidget.registry.pitchPrint = publicWidget.Widget.extend(VariantMixin, {
    selector: '#product_detail',
    events: {
        'click a.btn.btn-primary.js_check_product.a-submit': '_onClickAddToCart',
        'change input.product_id': '_onChangeProduct'
    },
    start: function () {
        if (typeof ppApiKey !== 'undefined' && ppApiKey !== null) {
            toggleLoader(true);
            let printDesign = localStorage.getItem("pp" + ppProductId);
            let mode = (printDesign != null ? "edit" : "new");
            let language_code = session.lang_url_code || navigator.language || navigator.userLanguage;
            language_code = language_code.substring(0, 2);
            if (debugMode) console.log(`Init PP client - designId: ${ppDesignId}, projectId: ${printDesign}`);
            ppClient = new PitchPrintClient({
                client: "od",
                apiKey: ppApiKey,
                designId: ppDesignId,
                product: { "id": ppProductId, "name": ppProductName },
                userId: ppUserEmail,
                custom: true,
                userData: { "email": ppUserEmail, "name": ppUserName },
                langCode: language_code,
                mode: mode,
                projectId: printDesign,
            });
            ppClient._ui.designSelect = document.getElementById("pp_design_select"); //Fix to overcome crash when using design observables module
            ppClient.on('app-validated', appValidated);
            ppClient.on('project-saved', projectSaved);
            ppClient.on('design-loaded', designLoaded);
            ppClient.on('template-color-changed', templateColourChanged);
            ppClient.on('editor-shown', editorShown);
        }
        return this._super.apply(this, arguments);
    },
    _onClickAddToCart: async function (ev) {
        //Add to cart clicked: Store PP project design to quote/sale order line
        try {
            let printDesign = localStorage.getItem("pp" + ppProductId);
            let variationsCount = localStorage.getItem("pp" + ppProductId + "vd");
            if (debugMode) console.log(`Adding to cart PP ID: ${printDesign}, Product ID: ${ppProductId}`);
            await jsonrpc('/shop/product/storedesign', {
                'id': printDesign,
                'product_id': ppProductId,
                'variations_count': variationsCount,
            }).then(() => {
                if (debugMode) console.log("Clearing localStorage");
                localStorage.clear();
            });
            if (debugMode) console.log("Passed storeDesignToOrder");
        } catch (err) { };
    },
    _onChangeProduct: function (ev) {
        //Call to a controller and get the PP product design
        let parent = $(ev.target).closest('.js_product');
        toggleCustomiseButtons(false);
        try {
            ppDesignId = null; // Clear any existing product designs
            ppProductId = this._getProductId(parent);
            //Call to a controller and get the default PP product design
            let route = '/shop/product/getdesign';
            let params = { "product_id": ppProductId };
            jsonrpc(route, params).then(function (data) {
                let printDesign = localStorage.getItem("pp" + ppProductId);
                let mode = (printDesign != null ? "edit" : "new");
                if (debugMode) console.log("Loading default design from Odoo product");
                if (data !== false) {
                    ppDesignId = data;
                    toggleCustomiseButtons(true);
                }
                toggleAddToCartButton(ppDesignId == null | mode == "edit");
            });
            //Render designs in image carousel
            if (ppProductId) displayCustomDesigns(ppProductId);
        } catch (err) { };
    },
});