{
    'name': 'Dreamwarez CRM',
    'version': '17.0.1.0.0',
    'summary': 'Customizations for CRM module',
    'description': """
        Dreamwarez CRM module
        ---------------------
        This module extends the base CRM functionality.
    """,
    'category': 'Sales/CRM',
    'author': 'Dreamwarez',
    'website': 'https://dreamwarez.com',
    'license': 'LGPL-3',
    'depends': ['base','crm','sale','sale_crm','dw_engineering_team','dw_sales'], 
    'data': [

        'security/crm_groups.xml',
        'security/crm_rules.xml',
        'security/ir.model.access.csv',         
        'data/crm_stage_data.xml',                    
        'views/crm_inherit.xml',
        'views/department_time_tracking.xml',
        'views/hide_filters.xml',
        
       ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
