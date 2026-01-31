{
    'name': 'ERP Labz Tax to GST',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Convert and rename taxes to GST format',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tax_to_gst_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/banner.svg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

