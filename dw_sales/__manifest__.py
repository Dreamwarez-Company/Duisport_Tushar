{
    'name': 'Dreamwarez Sales',
    'version': '17.0.1.0.0',
    'summary': 'Customizations for Sales module',
    'description': """
        Dreamwarez Sales module
        -----------------------
        This module extends the base Sales functionality, including support for confirming quotations into sales orders and linking to CRM leads.
    """,
    'category': 'Sales',
    'author': 'Dreamwarez',
    'website': 'https://dreamwarez.com',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'sale_crm','sale_management'],
    'data': [
        # 'views/sale_inherit_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}