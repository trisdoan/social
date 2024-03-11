/** @odoo-module **/

import {
    Component
} from "@odoo/owl";
import { useStore } from "./failed_message_storage";

export class FailedMessageList extends Component {
    static props = [
        "thread",
    ];
    static template = "mail_tracking.FailedMessageList";
    setup() {
        super.setup(...arguments)
        this.store = useStore
    }
    // FIXME: get list of failed messages in the current chatter
    _getNonReviewedFailedMessageItems(messageItems, reviewedMessageIds) {
        if (!messageItems.length) return [];
        return messageItems.filter(
            (item) => !reviewedMessageIds.has(item.message.id)
        );
    }

    // FIXME: featue when click -> toggle list of failed message
    _onClickTitle() {
        this.messageListView.toggleMessageFailedBoxVisibility();
    }
    isMessageFailedBoxVisible() {
        // add a 
    }
}
