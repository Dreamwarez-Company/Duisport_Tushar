from odoo import models, fields, api
from datetime import datetime


class BankReconciliationReport(models.AbstractModel):
    _name = 'report.all_reports_full.bank_reconciliation_template'
    _description = 'Bank Reconciliation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        
        journal_id = data.get('journal_id')
        date_to = data.get('date_to')
        
        if not journal_id or not date_to:
            return {}
        
        journal = self.env['account.journal'].browse(journal_id)
        
        # Get the bank account
        bank_account = journal.default_account_id
        
        # Get statement balance (last statement before date_to)
        statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', journal_id),
            ('date', '<=', date_to)
        ], order='date desc', limit=1)
        
        statement_balance = statement.balance_end_real if statement else 0.0
        
        # Get outstanding checks (payments not yet cleared)
        outstanding_checks = self.env['account.move.line'].search([
            ('account_id', '=', bank_account.id),
            ('date', '<=', date_to),
            ('reconciled', '=', False),
            ('debit', '>', 0),
            ('move_id.state', '=', 'posted'),
            ('parent_state', '=', 'posted')
        ])
        
        # Get outstanding deposits (receipts not yet cleared)
        outstanding_deposits = self.env['account.move.line'].search([
            ('account_id', '=', bank_account.id),
            ('date', '<=', date_to),
            ('reconciled', '=', False),
            ('credit', '>', 0),
            ('move_id.state', '=', 'posted'),
            ('parent_state', '=', 'posted')
        ])
        
        # Get book balance from account
        domain = [
            ('account_id', '=', bank_account.id),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('parent_state', '=', 'posted')
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        book_balance = sum(move_lines.mapped('debit')) - sum(move_lines.mapped('credit'))
        
        # Calculate totals
        total_outstanding_checks = sum(outstanding_checks.mapped('debit'))
        total_outstanding_deposits = sum(outstanding_deposits.mapped('credit'))
        
        # Adjusted book balance
        adjusted_balance = statement_balance - total_outstanding_checks + total_outstanding_deposits
        
        # company = self.env.company
        
        return {
            'doc_ids': docids,
            'doc_model': 'account.journal',
            'docs': journal,
            'journal': journal,
            'date_to': date_to,
            'statement_balance': statement_balance,
            'outstanding_checks': outstanding_checks,
            'outstanding_deposits': outstanding_deposits,
            'total_outstanding_checks': total_outstanding_checks,
            'total_outstanding_deposits': total_outstanding_deposits,
            'book_balance': book_balance,
            'adjusted_balance': adjusted_balance,
            # 'company': company,
            # 'company_id': company,
        }


class BankReconciliationWizard(models.TransientModel):
    _name = 'bank.reconciliation.wizard'
    _description = 'Bank Reconciliation Report Wizard'

    journal_id = fields.Many2one('account.journal', string='Bank Journal', 
                                  domain=[('type', '=', 'bank')], required=True)
    date_to = fields.Date(string='Reconciliation Date', required=True, 
                          default=fields.Date.context_today)

    def print_report(self):
        data = {
            'journal_id': self.journal_id.id,
            'date_to': self.date_to,
        }
        return self.env.ref('all_reports_full.action_bank_reconciliation_report').report_action(self, data=data)