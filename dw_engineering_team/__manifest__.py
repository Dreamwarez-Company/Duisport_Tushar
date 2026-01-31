# -*- coding: utf-8 -*-
{
    'name': 'Engineering Team Analysis',
    'version': '1.0',
    'summary': 'Send CRM lead requirement to engineering team and capture engineering details',
    'author': 'You',
    'category': 'Tools',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'crm', 'dw_engineering_product'],
    'data': [
        # 'security/engineering_team_security.xml',
        'security/ir.model.access.csv',
        'views/engineering_team_view.xml',
        # 'views/crm_lead_inherit_view.xml',
    ],
    'installable': True,
    'application': False,
}
