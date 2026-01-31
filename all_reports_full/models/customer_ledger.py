from odoo import api, fields, models

class CustomerLedgerReportWizard(models.TransientModel):
    _name = "customer.ledger.report.wizard"
    _description = "Customer Ledger Report Wizard"

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    partner_ids = fields.Many2many(
        'res.partner',
        string="Customers",
        domain=[('customer_rank', '>', 0)],
        help="Leave empty to include all customers"
    )

    def action_print_pdf(self):
        return self.env.ref(
            "all_reports_full.action_customer_ledger_report_pdf"
        ).report_action(self)

    def get_report_data(self):
        """Extract customer ledger data"""

        AccountMoveLine = self.env['account.move.line']

        # Receivable accounts domain
        account_domain = [
            '|',
            ('account_id.account_type', '=', 'asset_receivable'),
            ('account_id.account_type', '=', 'receivable'),
        ]

        # Determine which customers to include
        # Check if partner_ids exists AND has records
        if self.partner_ids and len(self.partner_ids) > 0:
            # Specific customers selected
            customers = self.partner_ids
        else:
            # No customers selected - get ALL customers from the system
            customers = self.env['res.partner'].search([
                ('customer_rank', '>', 0)
            ], order='name')

        customers_data = []

        for customer in customers.sorted('name'):

            # Opening Balance
            opening_lines = AccountMoveLine.search(account_domain + [
                ('partner_id', '=', customer.id),
                ('date', '<', self.date_from),
                ('parent_state', '=', 'posted'),
            ])
            opening_balance = sum(opening_lines.mapped('balance'))

            # Period Transactions
            period_lines = AccountMoveLine.search(account_domain + [
                ('partner_id', '=', customer.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted'),
            ], order='date asc, id asc')

            # Skip empty customers
            if not period_lines and opening_balance == 0:
                continue

            entries = []
            running_balance = opening_balance

            for line in period_lines:
                running_balance += line.balance

                entries.append({
                    'date': line.date,
                    'ref': line.move_id.name or '',
                    'journal': line.journal_id.name,
                    'description': line.name or line.move_id.ref or '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': running_balance,
                })

            # Final structure
            customers_data.append({
                'customer_name': customer.name,
                'customer_id': customer.id,
                'opening_balance': opening_balance,
                'entries': entries,
                'closing_balance': running_balance,
                'total_debit': sum(e['debit'] for e in entries),
                'total_credit': sum(e['credit'] for e in entries),
            })

        return customers_data