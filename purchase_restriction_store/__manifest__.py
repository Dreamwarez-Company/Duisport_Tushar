{
    'name': 'Purchase Restriction for Store Department',
    'version': '17.0.1.0.0',
    'summary': 'Restrict Store Department to create only draft RFQs',
    'author': 'ChatGPT',
    'depends': ['purchase', 'base'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        # 'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
