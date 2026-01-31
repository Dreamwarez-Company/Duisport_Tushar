# -*- coding: utf-8 -*-
{
    'name': "DW Engineering Product",
    'summary': "Engineering details on product",
    'description': """
Long description of module's purpose
    """,
    'author': "DREAMWAREZ",
    'website': "https://www.yourcompany.com",
    'version': '0.1',
    'depends': ['base', 'product', 'mrp'],
    'data': [
        'security/engineering_team.xml',
        'views/product_engineering_view.xml',
        'views/bom_views.xml',
        'views/bom_line_views.xml',
        'security/ir.model.access.csv',   
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}
