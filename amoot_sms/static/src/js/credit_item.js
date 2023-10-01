odoo.define('amoot_sms.user_credit_item', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var ajax = require('web.ajax');
    var rpc = require('web.rpc');

    async function renderUserCreditItem() {
        if (this.$buttons) {
            var self = this;
            try {
                var userCredit = this.$buttons[0].children[3]
                userCredit.textContent = 'اعتبار پیامکی شما'
                //
                //     ajax.jsonRpc('/sms_wallet', 'call', {
                //         model: 'amoot.sms',
                //         method: 'read',
                //         args: [],
                //         kwargs: {},
                //     }).then(function (result) {
                //         console.log('provider', result); // Do something with the value
                //         userCredit.textContent = result + ' تومان '
                //     }).catch(function (err) {
                //         console.log('error', err)
                //         userCredit.textContent = 'اعتبار پیامکی شما'
                //     });
                rpc.query({
                    model: 'amoot.sms',
                    method: 'sms_wallet',
                    args: ['test'],
                }).then(function (result) {
                    console.log('provider', result); // Do something with the value
                    userCredit.textContent = result + ' تومان '
                }).catch(function (err) {
                    console.log('error', err)
                    userCredit.textContent = 'اعتبار پیامکی شما'

                });
            } catch (err) {
                console.log(err)

            }
        }
    }

    var UserSmsCreditItemListController = ListController.extend({
        buttons_template: 'UserSmsCreditItemListView.buttons',
        renderButtons: function () {
            this._super.apply(this, arguments);
            renderUserCreditItem.apply(this, arguments);
        }
    });

    var UserSmsCreditItemListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UserSmsCreditItemListController,
        }),

    });

    viewRegistry.add('amoot_sms_user_credit_tree', UserSmsCreditItemListView);

});
