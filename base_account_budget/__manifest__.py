
{
    'name': 'Odoo 17 Budget Management',
    'version': '17.0.1.0.2',
    'category': 'Accounting',
    'summary': """ Budget Management for Odoo 17 Community Edition. """,
    'depends': ['base', 'account'],
    'data': [
        'security/account_budget_security.xml',
        'security/ir.model.access.csv',
        'views/account_analytic_account_views.xml',
        'views/account_budget_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
