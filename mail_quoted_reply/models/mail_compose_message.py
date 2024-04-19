from markupsafe import Markup

from odoo import api, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    def _compute_body(self):
        res = super()._compute_body()
        for composer in self:
            context = composer._context
            if "is_quoted_reply" in context.keys() and context["is_quoted_reply"]:
                composer.body = Markup(context["quote_body"])
        return res

    @api.depends(
        "composition_mode", "model", "parent_id", "res_domain", "res_ids", "template_id"
    )
    def _compute_subject(self):
        res = super()._compute_subject()
        for composer in self:
            subj = composer._context.get("default_subject", False)
            if subj:
                composer.subject = tools.ustr(subj)
        return res
