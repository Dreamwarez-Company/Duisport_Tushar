{
    'name': 'DW Quality Check',
    'version': '1.0.0',
    'summary': 'Quality checklist for incoming shipments (stock pickings)',
    'category': 'Inventory/Quality',
    'author': 'Dreamwarez',
    'license': 'LGPL-3',
    'depends': ['stock', 'product', 'mail','mrp'],
    'data': [
        'security/quality_check_group.xml',
        'security/ir.model.access.csv',
        'views/quality_check.xml',
        'views/stock_picking.xml',
        'views/mrp_production.xml',
        
    ],
    'installable': True,
    'application': False,
}