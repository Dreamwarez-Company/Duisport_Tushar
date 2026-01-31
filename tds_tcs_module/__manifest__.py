{
    'name': 'Vendor TDS Auto Population',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'data/tds_section_data.xml',
        'views/tds_register_views.xml',
        'views/tds_register_report.xml',  
        'views/tds_section_wise_report_views.xml',
        'views/tds_section_wise_report_templates.xml',
        'views/tds_summary_report_views.xml',
        'views/tds_summary_report_templates.xml',
    ],
    'installable': True,
    'application': False,
}
