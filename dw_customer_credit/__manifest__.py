# -*- coding: utf-8 -*-
{
    'name': "dw_customer_credit",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base','sale', 'account','dw_sales','base_accounting_kit','stock', 'mrp'],

    'data': [
        'security/res_partner_onboarding_security.xml',
        'security/customer_onboarding_security.xml',        
        'security/fixed_asset_security.xml',
        'security/ir.model.access.csv',        
        'views/res_partner_onboarding_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/views.xml',
        'views/neft_register_wizard_view.xml', 
        'views/report_neft_register_template.xml',        
        'views/account_reports.xml',
        'views/report_cashflow_template.xml',
        'views/report_fixed_asset_register_template.xml',
        'views/report_depreciation_sheet_template.xml',
        'views/report_cwip_report_template.xml',
        'views/report_asset_disposal_template.xml',
        'views/report_inventory_costing_template.xml',
        'views/slow_moving_wizard_view.xml',
        'reports/reports_slow_nonmoving.xml',
        'reports/report_wip_valuation.xml',
        'reports/report_template_wip_valuation.xml',
        'views/cashflow_wizard_template.xml',

    ],
    'controllers': ['controllers/field_inspector'],
    
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}