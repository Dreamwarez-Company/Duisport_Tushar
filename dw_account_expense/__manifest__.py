{
    'name': 'DW Account Expense',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Manage payments, credit/debit notes, and expenses with tags',
    'description': 'Extend account.move and account.payment with x_expense_tag, plus expense records.',
    'author': 'DREAMWAREZ',
    'depends': ['base','account', 'hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/expense_tag_views.xml',
        'views/expense_record_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
}
