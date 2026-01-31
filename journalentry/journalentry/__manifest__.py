# -*- coding: utf-8 -*-
{
    'name': "journalentry",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['base','account', 'crm'],
    'depends': ['base', 'account','crm'],
    # always loaded
    'data': [
        # 'security/security.xml',
        # 'security/ir.model.access.csv',
        # 'data/voucher_type_data.xml',
        # 'views/journal_voucher_menu.xml',
        # 'views/journal_voucher_tree.xml',
        # 'views/journal_voucher_form.xml',
        # 'views/voucher_type_views.xml',

        # 'views/views.xml',
        # 'views/templates.xml',
        # 'views/vouchers_report_views.xml',

        # 'views/journal_voucher_form.xml',
        # 'views/journal_voucher_menu.xml',
        'security/ir.model.access.csv', # 取消这行的注释
        'views/vouchers_report_views.xml',
        # 'views/vouchers_report_print_wizard_views.xml',
        'views/journal_voucher_form.xml',
        'views/journal_voucher_menu.xml',
        # 'report/simple_vouchers_report.xml',  # Add this
        'report/vouchers_report_template.xml',
        
    ],
    'controllers': ['controllers/main.py'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'journalentry/static/src/css/journal_voucher.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}

