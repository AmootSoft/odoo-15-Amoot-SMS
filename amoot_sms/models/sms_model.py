from email.policy import default

from odoo import fields, models, api, _
import re
import json
from odoo.api import ondelete
from odoo.exceptions import ValidationError
import requests

class SMSProvider(models.Model):
    _name = 'amoot.sms'
    _description = 'sms provider configuration'

    title = fields.Char(string="Title")
    provider = fields.Selection(selection=[('amoot_sms', "Amoot SMS")], string='Provider', required=True)
    username = fields.Char(string='Username', required=True,
                           groups='amoot_sms.group_amoot_sms_read_write, amoot_sms.group_amoot_sms_full_access')
    password = fields.Char(string='Password', required=True,
                           groups='amoot_sms.group_amoot_sms_read_write, amoot_sms.group_amoot_sms_full_access')
    line_no = fields.Char(string='private line number or (public) or (service)', help='style: 09XXXXXXXXX (length = 11)',
                          required=True)
    is_default = fields.Boolean(string='Default', required=True, default=False)

    def sms_wallet(self):
        user = self.env['amoot.sms'].search([['is_default', '=', True]])
        if user:
            username = user['username']
            password = user['password']
            response = requests.request('POST', 'https://portal.amootsms.com/rest/AccountStatus',
                                    params={"UserName": username, "Password": password}
                                        )
            value = json.loads(response.text)
            RemaindCredit = value["RemaindCredit"]
            return RemaindCredit
        else:
            return 0

    def name_get(self):
        result = []
        for record in self:
            # name = record.title  # Customize the name display logic here
            result.append((record.id, f"{record.title}({record.provider})"))
        return result

    @api.constrains('is_default')
    def _check_is_default(self):
        defaults = self.env['amoot.sms'].search([['is_default', '=', True]])
        for record in self:
            rec_id = record.id
            if not defaults:
                record.is_default = True
            elif record.is_default:
                for item in defaults:
                    if item.id != rec_id:
                        item.is_default = False

    @api.constrains('line_no')
    def _check_line_no(self):
        for item in self:
            if item.provider == 'amoot_sms':
                if not (item.line_no.isdigit() or item.line_no == 'public' or item.line_no == 'service'):
                    raise ValidationError(_("شماره نامعتبر است"))

    @api.constrains('title')
    def _check_title(self):
        for item in self:
            title = item.title
            if not title or re.match(r"[\s]+", " " if not title else title):
                item.title = "NoTitle"


class PatternParameter(models.Model):
    _name = 'sms.pattern.parameter'

    parameter_name = fields.Char(required=True, string='Parameter name')
    model_name = fields.Many2one('ir.model', required=True, string='Model name', ondelete='cascade')
    field_name = fields.Many2one('ir.model.fields', required=True, string='Field name', ondelete='cascade')

    @api.onchange('model_name')
    def _onchange_model_name(self):
        if self.model_name:
            fields_data = self.env['ir.model.fields'].search([('model_id', '=', self.model_name.id)])
            self.field_name = False

            domain = [('id', 'in', fields_data.ids)]
            return {'domain': {'field_name': domain}}
        # todo if dont set model, dont show any fields


pattern_actions = [
    ('on_create', 'create'),
    ('on_modify', 'modify'),
    ('on_delete', 'delete'),
]


class SMSPattern(models.Model):
    _name = 'sms.pattern'

    pattern_name = fields.Char(required=True, string='Pattern Name')
    provider = fields.Many2one(comodel_name='amoot.sms', required=True, string='SMS Provider', ondelete='restrict')
    pattern_code = fields.Char(required=True, string='Pattern code')
    parameter = fields.Many2many(comodel_name='sms.pattern.parameter', required=False, string='Parameters',
                                 help='choose pattern parameters in order.',  ondelete='restrict')
    model_name = fields.Many2one('ir.model', required=True, string='Model name', ondelete='cascade')
    action = fields.Selection(selection=pattern_actions, string='Action', required=True)
