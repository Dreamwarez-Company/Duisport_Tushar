# -*- coding: utf-8 -*-
{
    'name': "dw_inventory_rule",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        'views/product_views.xml',
        # 'views/stock_views.xml',
        
        # 'views/product_tree_views.xml',    # New file for List view
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

 
    'installable': True,
    'application': False,
    'auto_install': False,
}

