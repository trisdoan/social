/* @odoo-module */
import {FailedMessage} from "../components/failed_message";
import {patch} from "@web/core/utils/patch";
import {Thread} from "@mail/core/common/thread";

patch(Thread, {
    components: {...Thread.components, FailedMessage},
});
