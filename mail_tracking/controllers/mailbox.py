from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.mailbox import MailboxController


class MailTrackingMailboxController(MailboxController):
    @http.route("/mail/failed/messages", methods=["POST"], type="json", auth="user")
    def discuss_failed_messages(
        self, search_term=None, before=None, after=None, limit=30, around=None
    ):
        res = request.env["mail.message"]._message_fetch(
            domain=[("is_failed_message", "=", True)],
            search_term=search_term,
            before=before,
            after=after,
            limit=limit,
            around=around,
        )
        return {**res, "messages": res["messages"].message_format()}
