from odoo import _, api, models
from odoo.addons.iap.tools import iap_tools as org_iap_tools
import contextlib
import logging
import json
import requests
import uuid
from unittest.mock import patch

from odoo import exceptions, _
from odoo.tests.common import BaseCase
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)
DEFAULT_ENDPOINT = 'https://portal.amootsms.com/webservice2.asmx'


class InsufficientCreditError(Exception):
    pass


def iap_jsonrpc(url, method='call', params=None, timeout=15,auto=None):
    """ SMS
    Calls the provided JSON-RPC endpoint, unwraps the result and
    returns JSON-RPC errors as exceptions.
    """
    payload = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': uuid.uuid4().hex,
    }
    _logger.info('iap jsonrpc %s', url)
    try:
        head = {'Content-Type': 'application/x-www-form-urlencoded'}
        req = None
        if params.get("messages"):
            for param in params['messages']:
                if auto != True:
                    mobiles=[param['Mobiles']]
                    res_ids = [param['res_id']]
                    try:
                        params['messages'][0]['Mobiles'] = ','.join(mobiles)
                        req = requests.post(url, data=params['messages'][0], timeout=timeout, headers=head)
                    except (ValueError, KeyError) as e:
                        _logger.error(e)
                else:
                    mobile = [param['Mobile']]
                    res_ids = [param['res_id']]
                    try:
                        params['messages'][0]['Mobile'] = ','.join(mobile)
                        req = requests.post(url, data=params['messages'][0], timeout=timeout, headers=head)
                    except (ValueError, KeyError) as e:
                        _logger.error(e)
        req.raise_for_status()
        response = req.json()
        # if not response['Data']:
        #     response['res_ids'] = res_ids
        """
        :response: dict of status {
                'res_ids': list: if msg failed to use payamak webservice (No Data)
                'Status': string: status of whole proccess,
                'Data': list of dict: [{
                    'Mobile': int: number,
                    'MessageID': int: 
                    'Status': string: status
                    'res_id': string: owj user
                } 
            }
        """
        if 'error' in response:
            name = response['error']['data'].get('name').rpartition('.')[-1]
            message = response['error']['data'].get('message')
            if name == 'InsufficientCreditError':
                e_class = InsufficientCreditError
            elif name == 'AccessError':
                e_class = exceptions.AccessError
            elif name == 'UserError':
                e_class = exceptions.UserError
            else:
                raise requests.exceptions.ConnectionError()
            e = e_class(message)
            e.data = response['error']['data']
            raise e
        return response
    except (ValueError, AttributeError, UnboundLocalError, requests.exceptions.ConnectionError,
            requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        raise exceptions.AccessError(
            _('Why Call Me :|| The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was %s',
              url))

class SmsApi(models.AbstractModel):
    _inherit = 'sms.api'

    @api.model
    def _contact_payamak_iap(self, local_endpoint, params, auto):
        """ Get Endpoint and params, then send request to amoot sms webservice """
        account = self.env['iap.account'].get('sms')
        params['account_token'] = account.account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint', DEFAULT_ENDPOINT)
        # TODO PRO, the default timeout is 15, do we have to increase it ?
        tmp = iap_jsonrpc(endpoint + local_endpoint, params=params, auto=auto)
        for i, j in enumerate(tmp['Data']):  # add res_id to returned data => will be use in _postprocess_iap_sent_sms
            j['res_id'] = int(params['messages'][i]['res_id'])
        return tmp

    @api.model
    def _send_sms(self, numbers, message):
        """ Send a single message to several numbers

        :param numbers: list of E164 formatted phone numbers
        :param message: content to send

        :raises ? TDE FIXME
        """
        defaults = self.env['amoot.sms'].search([['is_default', '=', True]])
        params = {
            'UserName': defaults.username,
            'Password': defaults.password,
            'SendDateTime': "",
            'SMSMessageText': message,
            'LineNumber': defaults.line_no,
            'Mobiles': numbers,
        }
        return self._contact_payamak_iap('/SendSimple_REST', params)


    @api.model
    def _send_sms_batch(self, messages, pattern=None, auto=None):
        """ Send SMS using IAP in batch mode
        :return: return of /iap/sms/1/send controller which is a list of dict [{
            'res_id': integer: ID of sms.sms,
            'Status':  string: 'insufficient_credit' or 'wrong_number_format' or 'success',
            'credit': integer: number of credits spent to send this SMS,
        }]
        :raises: normally none
        """
        if auto == True:
            local_endpoint = '/SendWithPattern_REST'
            params = {
                'UserName': pattern.provider.username,
                'Password': pattern.provider.password,
                'messages': messages
            }
        else:
            defaults = self.env['amoot.sms'].search([['is_default', '=', True]])
            local_endpoint = '/SendSimple_REST'
            params = {
                    'UserName': defaults.username,
                    'Password': defaults.password,
                    'messages': messages
                }
        return self._contact_payamak_iap(local_endpoint, params, auto)

    @api.model
    def _get_sms_api_error_messages(self):
        """ Returns a dict containing the error message to display for every known error 'state'
        resulting from the '_send_sms_batch' method.
        We prefer a dict instead of a message-per-error-state based method so we only call
        the 'get_credits_url' once, to avoid extra RPC calls. """

        buy_credits_url = self.sudo().env['iap.account'].get_credits_url(service_name='sms')
        buy_credits = '<a href="%s" target="_blank">%s</a>' % (
            buy_credits_url,
            _('Buy credits.')
        )
        return {
            'unregistered': _("You don't have an eligible IAP account."),
            'insufficient_credit': ' '.join([_('You don\'t have enough credits on your IAP account.'), buy_credits]),
            'wrong_number_format': _("The number you're trying to reach is not correctly formatted."),
        }



