/** @odoo-module **/

import {Message} from "@mail/core/common/message";

export class FailedMessage extends Message {
    static template = "mail_tracking.FailedMessage";
    static props = {
        isFailedMessage: true
    }
}
