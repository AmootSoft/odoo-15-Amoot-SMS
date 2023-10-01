import json
from odoo import http
from odoo.http import request
import requests


class SmsController(http.Controller):
    @http.route('/sms_wallet', auth='public', type='json', methods=['POST'])
    def sms_wallet(self):
        request.cr.execute("select * from amoot_sms where is_default = TRUE")
        val = request.cr.fetchall()
        if val:
            username = val[0][3]
            password = val[0][4]
            response = requests.get('https://portal.amootsms.com/rest/AccountStatus',
                                    params={"UserName": username, "Password": password})
            value = json.loads(response.text)
            RemaindCredit = value["RemaindCredit"]
            return RemaindCredit
        else:
            return 0
