/* @odoo-module */

import {Message} from "@mail/core/common/message";
import {patch} from "@web/core/utils/patch";
import {FailedMessage} from "../components/failed_message";
import {useStore} from "../components/failed_message_storage";

patch(Message, {
    components: {...Message.components, FailedMessage},
});

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.store = useStore();
    },
    _addMessageIdToStore(messageID) {
        this.store.addMessage(messageID);
    },
    get PartnerTrackings() {
        return this.props.message.partner_trackings;
    },
    _onTrackingStatusClick(ev) {
        var tracking_email_id = $(ev.currentTarget).data("tracking");
        ev.preventDefault();
        return this.env.services.action.doAction({
            type: "ir.actions.act_window",
            view_type: "form",
            view_mode: "form",
            res_model: "mail.tracking.email",
            views: [[false, "form"]],
            target: "new",
            res_id: tracking_email_id,
        });
    },
    async _onMarkFailedMessageReviewed(event) {
        event.preventDefault();
        const messageID = $(event.currentTarget).data("message-id");
        const messageNeedsAction = await this._markFailedMessageReviewed(messageID);
        // Add the reviewed message ID to storage so it is excluded from the list of rendered messages
        if (!messageNeedsAction) {
            this._addMessageIdToStore(messageID);
        }
    },
    _markFailedMessageReviewed(id) {
        return this.messageService.orm.call("mail.message", "set_need_action_done", [
            id,
        ]);
    },
    _onRetryFailedMessage(event) {
        event.preventDefault();
        const messageID = $(event.currentTarget).data("message-id");
        this.env.services.action.doAction("mail.mail_resend_message_action", {
            additionalContext: {
                mail_message_to_resend: messageID,
            },
            onClose: async () => {
                // Check if message is still 'failed' after Retry, and if it is not, add its ID to storage so
                // it is excluded from the list of rendered messages
                const failedMessages = await this.messageService.orm.call(
                    "mail.message",
                    "get_failed_messages",
                    [messageID]
                );
                const failedMessageIds = failedMessages.map((message) => {
                    return (message || {}).id;
                });
                if (failedMessageIds.length && !failedMessageIds.includes(messageID))
                    this._addMessageIdToStore(messageID);
            },
        });
    },
});
