
{
    'name': 'Vendor TDS Auto Population (India)',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Auto TDS section and rate based on vendor residency',
    'description': 'Adds residency-based TDS section selection and auto tax rate population for vendors',
    'author': 'Custom',
    'depends': ['account'],
    'data': [
        'views/res_partner_view.xml',
        'data/tds_section_data.xml',
    ],
    'installable': True,
    'application': False
}
