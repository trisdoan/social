# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from unittest.mock import patch

import odoo
from odoo.fields import Command
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo

mock_send_email = "odoo.addons.base.models.ir_mail_server." "IrMailServer.send_email"


class FakeUserAgent:
    browser = "Test browser"
    platform = "Test platform"

    def __str__(self):
        """Return name"""
        return "Test suite"


class TestMailTracking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sender = cls.env["res.partner"].create(
            {"name": "Test sender", "email": "sender@example.com"}
        )
        cls.recipient = cls.env["res.partner"].create(
            {"name": "Test recipient", "email": "recipient@example.com"}
        )

    def test_empty_email(self):
        self.recipient.write({"email_bounced": True})
        self.recipient.write({"email": False})
        self.assertEqual(False, self.recipient.email)
        self.assertEqual(False, self.recipient.email_bounced)
        self.recipient.write({"email_bounced": True})
        self.recipient.write({"email": ""})
        self.assertEqual(False, self.recipient.email_bounced)
        self.assertEqual(False, self.env["mail.tracking.email"].email_is_bounced(False))
        self.assertEqual(
            0.0, self.env["mail.tracking.email"].email_score_from_email(False)
        )

    def test_recipient_address_compute(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.write({"recipient": False})
        self.assertEqual(False, tracking.recipient_address)

    def test_message_post(self):
        # This message will generate a notification for recipient
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message.is_thread_message():
            self.env[message.model].browse(message.res_id)._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", self.recipient.id),
            ]
        )
        # The tracking email must be sent
        self.assertTrue(tracking_email)
        self.assertEqual(tracking_email.state, "sent")
        # message_dict read by web interface
        message_dict = message.message_format()[0]
        self.assertTrue(message_dict["history_partner_ids"])
        # First partner is recipient
        partner_id = message_dict["history_partner_ids"][0]
        self.assertEqual(partner_id, self.recipient.id)
        status = message_dict["partner_trackings"][0]
        # Tracking status must be sent and
        # mail tracking must be the one search before
        self.assertEqual(status["status"], "sent")
        self.assertEqual(status["tracking_id"], tracking_email.id)
        self.assertEqual(status["recipient"], self.recipient.display_name)
        self.assertEqual(status["partner_id"], self.recipient.id)
        self.assertEqual(status["isCc"], False)
        # And now open the email
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
        }
        tracking_email.event_create("open", metadata)
        self.assertEqual(tracking_email.state, "opened")

    def test_message_post_partner_no_email(self):
        # Create message with recipient without defined email
        self.recipient.write({"email": False})
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message.is_thread_message():
            self.env[message.model].browse(message.res_id).with_context(
                do_not_send_copy=True
            )._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", self.recipient.id),
            ]
        )
        # No email should generate a error state: no_recipient
        self.assertEqual(tracking_email.state, "error")
        self.assertEqual(tracking_email.error_type, "no_recipient")
        self.assertFalse(self.recipient.email_bounced)

    def _check_partner_trackings_cc(self, message):
        message_dict = message.message_format()[0]
        self.assertEqual(len(message_dict["partner_trackings"]), 5)
        # mail cc
        foundPartner = False
        foundNoPartner = False
        for tracking in message_dict["partner_trackings"]:
            if tracking["partner_id"] == self.sender.id:
                foundPartner = True
                self.assertTrue(tracking["isCc"])
            elif tracking["recipient"] == "unnamed@test.com":
                foundNoPartner = True
                self.assertFalse(tracking["partner_id"])
                self.assertTrue(tracking["isCc"])
            elif tracking["partner_id"] == self.recipient.id:
                self.assertFalse(tracking["isCc"])
        self.assertTrue(foundPartner)
        self.assertTrue(foundNoPartner)

    def test_email_cc(self):
        sender_user = self.env["res.users"].create(
            {
                "name": "Sender User Test",
                "partner_id": self.sender.id,
                "login": "sender-test",
            }
        )
        # pylint: disable=C8107
        message = self.recipient.with_user(sender_user).message_post(
            body="<p>This is a test message</p>",
            email_cc="Dominique Pinon <unnamed@test.com>, sender@example.com",
        )
        # suggested recipients
        recipients = self.recipient._message_get_suggested_recipients()
        suggested_mails = {email[1] for email in recipients[self.recipient.id]}
        self.assertIn("unnamed@test.com", suggested_mails)
        self.assertEqual(len(recipients[self.recipient.id]), 3)
        # Repeated Cc recipients
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "email_cc": "Dominique Pinon <unnamed@test.com>, sender@example.com"
                ", recipient@example.com",
                "body": "<p>This is another test message</p>",
            }
        )
        if message.is_thread_message():
            self.env[message.model].browse(message.res_id)._notify_thread(message)
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients[self.recipient.id]), 3)
        self._check_partner_trackings_cc(message)

    def _check_partner_trackings_to(self, message):
        message_dict = message.message_format()[0]
        self.assertEqual(len(message_dict["partner_trackings"]), 6)
        # mail cc
        foundPartner = False
        foundNoPartner = False
        for tracking in message_dict["partner_trackings"]:
            if tracking["partner_id"] == self.sender.id:
                foundPartner = True
            elif tracking["recipient"] == "support+unnamed@test.com":
                foundNoPartner = True
                self.assertFalse(tracking["partner_id"])
        self.assertTrue(foundPartner)
        self.assertTrue(foundNoPartner)

    def test_email_to(self):
        sender_user = self.env["res.users"].create(
            {
                "name": "Sender User Test",
                "partner_id": self.sender.id,
                "login": "sender-test",
            }
        )
        # pylint: disable=C8107
        message = self.recipient.with_user(sender_user).message_post(
            body="<p>This is a test message</p>",
            email_to="Dominique Pinon <support+unnamed@test.com>, sender@example.com",
        )
        # suggested recipients
        recipients = self.recipient._message_get_suggested_recipients()
        suggested_mails = {email[1] for email in recipients[self.recipient.id]}
        self.assertIn("support+unnamed@test.com", suggested_mails)
        self.assertEqual(len(recipients[self.recipient.id]), 3)
        # Repeated To recipients
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "email_to": "Dominique Pinon <support+unnamed@test.com>"
                ", sender@example.com, recipient@example.com"
                ", TheCatchall@test.com",
                "body": "<p>This is another test message</p>",
            }
        )
        if message.is_thread_message():
            self.env[message.model].browse(message.res_id)._notify_thread(message)
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients[self.recipient.id]), 4)
        self._check_partner_trackings_to(message)
        # Catchall + Alias
        # TODO check how to create domain and alias in v17.
        domain = self.env["mail.alias.domain"].create(
            {"name": "test.com", "catchall_alias": "catchall"}
        )
        self.env["mail.alias"].create(
            [
                {
                    "alias_model_id": self.env["ir.model"]._get("res.partner").id,
                    "alias_name": "support+unnamed",
                    "alias_domain_id": domain.id,
                },
                {
                    "alias_model_id": self.env["ir.model"]._get("res.partner").id,
                    "alias_name": "thecatchall",
                    "alias_domain_id": domain.id,
                },
            ]
        )
        recipients = self.recipient._message_get_suggested_recipients()
        self.assertEqual(len(recipients[self.recipient.id]), 2)
        suggested_mails = {email[1] for email in recipients[self.recipient.id]}
        self.assertNotIn("support+unnamed@test.com", suggested_mails)

    def test_failed_message(self):
        MailMessageObj = self.env["mail.message"]
        # Create message
        mail, tracking = self.mail_send(self.recipient.email)
        self.assertFalse(tracking.mail_message_id.mail_tracking_needs_action)
        # Force error state
        tracking.state = "error"
        self.assertTrue(tracking.mail_message_id.mail_tracking_needs_action)
        failed_count = MailMessageObj.get_failed_count()
        self.assertTrue(failed_count > 0)
        values = tracking.mail_message_id.get_failed_messages()
        self.assertEqual(values[0]["id"], tracking.mail_message_id.id)
        messages = MailMessageObj.search([])
        messages_failed = MailMessageObj.search([["is_failed_message", "=", True]])
        self.assertTrue(messages)
        self.assertTrue(messages_failed)
        self.assertTrue(len(messages) > len(messages_failed))
        tracking.mail_message_id.set_need_action_done()
        self.assertFalse(tracking.mail_message_id.mail_tracking_needs_action)
        self.assertTrue(MailMessageObj.get_failed_count() < failed_count)
        # No author_id
        tracking.mail_message_id.author_id = False
        values = tracking.mail_message_id.get_failed_messages()[0]
        if values and values.get("author"):
            self.assertEqual(values["author"][0], -1)

    def test_resend_failed_message(self):
        # This message will generate a notification for recipient
        message = self.env["mail.message"].create(
            {
                "subject": "Message test",
                "author_id": self.sender.id,
                "email_from": self.sender.email,
                "message_type": "comment",
                "model": "res.partner",
                "res_id": self.recipient.id,
                "partner_ids": [Command.link(self.recipient.id)],
                "body": "<p>This is a test message</p>",
            }
        )
        if message.is_thread_message():
            self.env[message.model].browse(message.res_id)._notify_thread(message)
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [
                ("mail_message_id", "=", message.id),
                ("partner_id", "=", self.recipient.id),
            ]
        )
        # Force error state
        tracking_email.state = "error"
        # Create resend mail wizard
        wizard = (
            self.env["mail.resend.message"]
            .sudo()
            .with_context(mail_message_to_resend=message.id)
            .create({})
        )
        # Check failed recipients
        self.assertTrue(any(wizard.partner_ids))
        self.assertEqual(self.recipient.email, wizard.partner_ids[0].email)
        # Resend message
        wizard.resend_mail_action()
        # Check tracking reset
        self.assertFalse(tracking_email.state)

    def mail_send(self, recipient):
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "email_from": "from@domain.com",
                "email_to": recipient,
                "body_html": "<p>This is a test message</p>",
            }
        )
        mail.send()
        # Search tracking created
        tracking_email = (
            self.env["mail.tracking.email"].sudo().search([("mail_id", "=", mail.id)])
        )
        return mail, tracking_email

    def test_concurrent_open(self):
        mail, tracking = self.mail_send(self.recipient.email)
        ts = time.time()
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
            "timestamp": ts,
        }
        # First open event
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 1)
        # Concurrent open event
        metadata["timestamp"] = ts + 2
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 1)
        # Second open event
        metadata["timestamp"] = ts + 350
        tracking.event_create("open", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "open")
        self.assertEqual(len(opens), 2)

    def test_concurrent_click(self):
        mail, tracking = self.mail_send(self.recipient.email)
        ts = time.time()
        metadata = {
            "ip": "127.0.0.1",
            "user_agent": "Odoo Test/1.0",
            "os_family": "linux",
            "ua_family": "odoo",
            "timestamp": ts,
            "url": "https://www.example.com/route/1",
        }
        # First click event (URL 1)
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 1)
        # Concurrent click event (URL 1)
        metadata["timestamp"] = ts + 2
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 1)
        # Second click event (URL 1)
        metadata["timestamp"] = ts + 350
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 2)
        # Concurrent click event (URL 2)
        metadata["timestamp"] = ts + 2
        metadata["url"] = "https://www.example.com/route/2"
        tracking.event_create("click", metadata)
        opens = tracking.tracking_event_ids.filtered(lambda r: r.event_type == "click")
        self.assertEqual(len(opens), 3)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_smtp_error(self):
        with patch(mock_send_email) as mock_func:
            mock_func.side_effect = Warning("Test error")
            mail, tracking = self.mail_send(self.recipient.email)
            self.assertEqual("error", tracking.state)
            self.assertEqual("Warning", tracking.error_type)
            self.assertEqual("Test error", tracking.error_description)
            self.assertTrue(self.recipient.email_bounced)

    def test_partner_email_change(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("open", {})
        orig_score = self.recipient.email_score
        orig_count = self.recipient.tracking_emails_count
        orig_email = self.recipient.email
        self.recipient.email = orig_email + "2"
        self.assertEqual(50.0, self.recipient.email_score)
        self.assertEqual(0, self.recipient.tracking_emails_count)
        self.recipient.email = orig_email
        self.assertEqual(orig_score, self.recipient.email_score)
        self.assertEqual(orig_count, self.recipient.tracking_emails_count)

    def test_process_hard_bounce(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("hard_bounce", {})
        self.assertEqual("bounced", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_soft_bounce(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("soft_bounce", {})
        self.assertEqual("soft-bounced", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_delivered(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("delivered", {})
        self.assertEqual("delivered", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_deferral(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("deferral", {})
        self.assertEqual("deferred", tracking.state)

    def test_process_spam(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("spam", {})
        self.assertEqual("spam", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_unsub(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("unsub", {})
        self.assertEqual("unsub", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_reject(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("reject", {})
        self.assertEqual("rejected", tracking.state)
        self.assertTrue(self.recipient.email_score < 50.0)

    def test_process_open(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("open", {})
        self.assertEqual("opened", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_click(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("click", {})
        self.assertEqual("opened", tracking.state)
        self.assertTrue(self.recipient.email_score > 50.0)

    def test_process_several_bounce(self):
        for _i in range(1, 10):
            mail, tracking = self.mail_send(self.recipient.email)
            tracking.event_create("hard_bounce", {})
            self.assertEqual("bounced", tracking.state)
        self.assertEqual(0.0, self.recipient.email_score)

    def test_bounce_new_partner(self):
        mail, tracking = self.mail_send(self.recipient.email)
        tracking.event_create("hard_bounce", {})
        new_partner = self.env["res.partner"].create({"name": "Test New Partner"})
        new_partner.email = self.recipient.email
        self.assertTrue(new_partner.email_bounced)

    def test_recordset_email_score(self):
        """For backwords compatibility sake"""
        trackings = self.env["mail.tracking.email"]
        for _i in range(11):
            mail, tracking = self.mail_send(self.recipient.email)
            tracking.event_create("click", {})
            trackings |= tracking
        self.assertEqual(100.0, trackings.email_score())

    def test_bounce_tracking_event_created(self):
        mail, tracking = self.mail_send(self.recipient.email)
        message = self.env.ref("mail.mail_message_channel_1_1")
        message.mail_tracking_ids = [Command.link(tracking.id)]
        mail.mail_message_id = message
        message_dict = {
            "bounced_email": "test@test.net",
            "bounced_message": message,
            "bounced_msg_ids": [message.message_id],
            "bounced_partner": self.recipient,
            "cc": "",
            "date": "2023-02-07 12:35:53",
            "email_from": "MAILER-DAEMON@eu-west-1.amazonses.com",
            "from": "MAILER-DAEMON@eu-west-1.amazonses.com",
            "in_reply_to": "<010201864d109aa7-west-1.amazonses.com>",
            "is_internal": False,
            "message_id": "<010201862be01f29-west-1.amazonses.com>",
            "message_type": "email",
            "parent_id": 15894917,
            "partner_ids": [],
            "recipients": "bounce+694942@recipient.net",
            "references": "<010201862bdfa5e9-west-1.amazonses.com>",
            "subject": "bounce notification",
            "to": "bounce+694942-mailing.contact-836@test.net",
        }
        self.env["mail.thread"]._routing_handle_bounce(message, message_dict)
        self.assertTrue(
            "soft_bounce"
            in message.mail_tracking_ids.tracking_event_ids.mapped("event_type")
        )

    def test_tracking_img_tag(self):
        # As the img tag is not in the body of the returned mail.mail record,
        # we have to intercept the IrMailServer.send_email method here to get
        # the real outgoing mail body and check for the img tag with a
        # side_effect function:
        def assert_tracking_tag_side_effect(*args, **kwargs):
            mail = args[0]
            msg = "data-odoo-tracking-email not found"
            if "data-odoo-tracking-email=" in mail.as_string():
                msg = "data-odoo-tracking-email found"
            raise AssertionError(msg)

        with patch(mock_send_email) as mock_func:
            mock_func.side_effect = assert_tracking_tag_side_effect
            self.env["ir.config_parameter"].set_param(
                "mail_tracking.tracking_img_disabled", False
            )
            mail, tracking = self.mail_send(self.recipient.email)
            self.assertEqual(
                "data-odoo-tracking-email found", tracking.error_description
            )

            # now we change the system parameter "mail_tracking.img.disable"
            # to True and check that the img tag is not in the outgoing mail
            self.env["ir.config_parameter"].set_param(
                "mail_tracking.tracking_img_disabled", True
            )
            mail, tracking = self.mail_send(self.recipient.email)
            self.assertEqual(
                "data-odoo-tracking-email not found", tracking.error_description
            )

    def test_unlink_mail_alias(self):
        self.env["ir.config_parameter"].search([], limit=1).unlink()


@odoo.tests.tagged("-at_install", "post_install")
class TestMailTrackingHttp(HttpCaseWithUserDemo, TestMailTracking):
    def mail_send(self, recipient):
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "email_from": "from@domain.com",
                "email_to": recipient,
                "body_html": "<p>This is a test message</p>",
            }
        )
        mail.send()
        # Search tracking created
        tracking_email = (
            self.env["mail.tracking.email"].sudo().search([("mail_id", "=", mail.id)])
        )
        return mail, tracking_email

    def test_mail_send(self):
        self.authenticate(None, None)
        db = self.env.cr.dbname
        mail, tracking = self.mail_send(self.recipient.email)
        self.assertEqual(mail.email_to, tracking.recipient)
        self.assertEqual(mail.email_from, tracking.sender)
        res = self.url_open(
            url="/mail/tracking/open/%s/%s/%s/blank.gif"  # noqa UP031
            % (db, tracking.id, tracking.token),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        # Two events: sent and open
        self.assertEqual(2, len(tracking.tracking_event_ids))
        # Fake event: tracking_email_id = False
        self.url_open(
            url="/mail/tracking/open/%s/%s/%s/blank.gif" % (db, False, False),  # noqa UP031
            headers={"Content-Type": "application/json"},
        )
        # Two events again because no tracking_email_id found for False
        self.assertEqual(2, len(tracking.tracking_event_ids))

    def test_mail_tracking_open(self):
        self.authenticate(None, None)
        db = self.env.cr.dbname
        _, tracking = self.mail_send(self.recipient.email)
        # Tracking is in sent or delivered state. But no token give.
        # Do not generates tracking event
        self.url_open(
            url="/mail/tracking/open/%s/%s/%s/blank.gif" % (db, tracking.id, False),  # noqa UP031
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(1, len(tracking.tracking_event_ids))
        tracking.write({"state": "opened"})
        # Tracking isn't in sent or delivered state.
        # Don't generates tracking event
        self.url_open(
            url=f"/mail/tracking/open/{db}/{tracking.id}/{tracking.token}/blank.gif",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(1, len(tracking.tracking_event_ids))
        tracking.write({"state": "sent"})
        # Tracking is in sent or delivered state and a token is given.
        # Generates tracking event
        self.url_open(
            url=f"/mail/tracking/open/{db}/{tracking.id}/{tracking.token}/blank.gif",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(2, len(tracking.tracking_event_ids))
        # Generate new email due concurrent event filter
        _, tracking = self.mail_send(self.recipient.email)
        tracking.write({"token": False})
        # Tracking is in sent or delivered state but a token is given for a
        # record that doesn't have a token.
        # Don't generates tracking event
        self.url_open(
            url=f"/mail/tracking/open/{db}/{tracking.id}/tokentest/blank.gif",  # noqa E501
            headers={"Content-Type": "application/json"},
        )
        # Tracking is in sent or delivered state and not token is given for
        # a record that doesn't have a token.
        # Generates tracking event
        self.url_open(
            url="/mail/tracking/open/%s/%s/blank.gif" % (db, tracking.id),  # noqa UP031
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(2, len(tracking.tracking_event_ids))
