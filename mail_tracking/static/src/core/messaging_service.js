/* @odoo-module */

import {Messaging} from "@mail/core/common/messaging_service";
import { _t } from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Messaging.prototype, {
    setup(env, service) {
        super.setup(...arguments)
        this.store.discuss.failed = {
            id: "failed",
            model: "mail.box",
            name: _t("Failed"),
            type: "mailbox",
            counter: 0,
        };
    },
    initMessagingCallback(data) {
        super.initMessagingCallback(...arguments)
        this.store.discuss.failed.counter = data.failed_counter
    }
});
