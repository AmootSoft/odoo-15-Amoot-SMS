# -*- coding: utf-8 -*-
# Part of owj. See LICENSE file for full copyright and licensing details.

import logging
import threading

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError,UserError ,RedirectWarning
from odoo.tools import html_escape


_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = 'sms.sms'

    state = fields.Selection([
        ('outgoing', 'In Queue'),
        ('sent', 'Sent'),
        ('error', 'Error'),
        ('canceled', 'Canceled')
    ], 'SMS Status', readonly=True, copy=False, default='sent', required=True)

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        if self.env["ir.module.module"].search([['name', '=', 'amoot_sms']])[0].state == "installed":
            defaults = self.env['amoot.sms'].search([['is_default', '=', True]])
            if defaults:
                iap_data = [{
                        'res_id': record.id,
                        'UserName': defaults.username,
                        'Password': defaults.password,
                        'SendDateTime': "2023-02-01-18:50",
                        'SMSMessageText': record.body,
                        'LineNumber': defaults.line_no,
                        'Mobiles': record.number,
                    } for record in self]
                try:
                    iap_results = self.env['sms.api']._send_sms_batch(iap_data)
                except Exception as e:
                    _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
                    if raise_exception:
                        raise self._postprocess_iap_sent_sms(
                            [{'res_id': sms.id, 'Status': 'server_error'} for sms in self],
                            unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                else:
                    _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)
                    self._postprocess_iap_sent_sms(iap_results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)

            else:
                action = self.env.ref('amoot_sms.action_amoot_sms_view')
                msg = _('لطفا درگاه پیامکی خود را قبل از اقدام به ارسال پیامک تعریف کنید.')
                raise RedirectWarning(msg, action.id, _('برو به تنظیمات پیامک'))

        else:
            raise UserError(_("لطفا ابتدا ماژول پیامک را نصب کنید"))

    def _send_action(self, module_name, action, vals_list, pid, auto, number, unlink_failed=False, unlink_sent=True,
                     raise_exception=False):
        pattern = self.env['sms.pattern'].search([['action', '=', action], ['model_name', '=', module_name]])
        pattern = pattern[0]
        if pattern:
            if pattern.action == "on_create":
                result = []
                for item in pattern.parameter.field_name:
                    if vals_list[0][item.name] != False:
                        result.append(vals_list[0][item.name])
                """ This method tries to send SMS after checking the number (presence and
                formatting). """
                value = ",".join(result)
                iap_data = [{
                    "res_id": pid,
                    "UserName": pattern.provider.username,
                    "Password": pattern.provider.password,
                    "Mobile": number,
                    "PatternCodeID": pattern.pattern_code,
                    "PatternValues": value,
                }]
                try:
                    iap_results = self.env['sms.api']._send_sms_batch(iap_data, pattern, auto)
                except Exception as e:
                    _logger.info('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
                    if raise_exception:
                        raise self._postprocess_iap_sent_sms(
                            [{'res_id': sms.id, 'Status': 'server_error'} for sms in self],
                            unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                else:
                    _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, iap_results)
            elif pattern.action == "on_modify":
                pass
            elif pattern.action == "on_delete":
                pass
            else:
                # todo reminder
                pass
        else:
            raise UserError(_("لطفا الگو پیامکی خود را انتخاب کنید تا در زمان ساخت مخاطب جدید پیام ارسال شود."))

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, unlink_failed=False, unlink_sent=True):
        todelete_sms_ids = []
        if unlink_failed:
            todelete_sms_ids += [item['res_id'] for item in iap_results['Data'] if item['Status'].lower() != 'success']
        if unlink_sent:
            todelete_sms_ids += [item['res_id'] for item in iap_results['Data'] if item['Status'].lower() == 'success']
        for state in self.IAP_TO_SMS_STATE.keys():
            sms_ids = [item['res_id'] for item in iap_results['Data'] if item['Status'].lower() == state]
            if sms_ids:
                if state != 'success' and not unlink_failed:
                    self.env['sms.sms'].sudo().browse(sms_ids).write({
                        'state': 'error',
                        'failure_type': self.IAP_TO_SMS_STATE[state],
                    })
                if state == 'success' and unlink_sent:
                    self.env['sms.sms'].sudo().browse(sms_ids).write({
                        'state': 'sent',
                        'failure_type': False,
                    })
                notifications = self.env['mail.notification'].sudo().search([
                    ('notification_type', '=', 'sms'),
                    ('sms_id', 'in', sms_ids),
                    ('notification_status', 'not in', ('sent', 'canceled')),
                ])
                if notifications:
                    notifications.write({
                        'notification_status': 'sent' if state == 'success' else 'exception',
                        'failure_type': self.IAP_TO_SMS_STATE[state] if state != 'success' else False,
                        'failure_reason': failure_reason if failure_reason else False,
                    })
        self.mail_message_id._notify_message_notification_update()
        # if todelete_sms_ids:
        #     self.browse(todelete_sms_ids).sudo().unlink()

