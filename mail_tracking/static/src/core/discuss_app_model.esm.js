/* @odoo-module */

import {DiscussApp} from "@mail/core/common/discuss_app_model";
import {Record} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";

patch(DiscussApp.prototype, {
    setup() {
        super.setup();
        this.failed = Record.one("Thread");
    },
});
