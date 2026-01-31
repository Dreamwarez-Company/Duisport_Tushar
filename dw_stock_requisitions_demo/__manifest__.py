# -*- coding: utf-8 -*-
{
    'name': "dw_stock_requisitions_demo",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock', 'mrp', 'hr','product','mail', 'uom','purchase'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        # 'wizard/purchase_order_wizard.py',
        'views/mrp_requisition_views.xml',           # Main views
        'views/manufacturing_menus.xml',             # Menus
        'views/stock_picking_views.xml',             # Other views
        'views/mrp_production_views.xml',            # Inherited views
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

