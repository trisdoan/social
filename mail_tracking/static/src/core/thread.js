/* @odoo-module */

import {Thread} from "@mail/core/common/thread";
import {patch} from "@web/core/utils/patch";
import { FailedMessage } from "../components/failed_message";
import { FailedMessageList } from "../components/failed_message_list";

patch(Thread, {
    components: {...Thread.components, FailedMessage, FailedMessageList},
});
