{
    'name': 'Amoot sms',
    'version': '1.0.0',
    'summary': 'SMS Provider Configuration',
    'description': 'Description',
    'category': 'SMS',
    'author': 'Amoot',
    'website': 'https://amootsoft.com',
    'depends': ['base', 'sms'],
    'data': [
        'security/amoot_sms_security.xml',
        'security/ir.model.access.csv',
        'views/provider_views.xml',
        'views/sms_pattern_views.xml',
        # 'views/menu.xml',
        'views/user_credit_views.xml',
        'views/amoot_sms_settings_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'amoot_sms/static/src/js/**/*',
        ],
        'web.assets_qweb': [
            'amoot_sms/static/src/xml/**/*',
        ],
    },
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
