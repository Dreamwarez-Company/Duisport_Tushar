from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class VendorLedgerReportWizard(models.TransientModel):
    _name = "vendor.ledger.report.wizard"
    _description = "Vendor Ledger Report Wizard"
    
    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    partner_ids = fields.Many2many(
        'res.partner', 
        string="Vendors",
        domain=[('supplier_rank', '>', 0)],
        help="Leave empty to include all vendors"
    )
    
    def action_print_pdf(self):
        return self.env.ref(
            "all_reports_full.action_vendor_ledger_report_pdf"
        ).report_action(self)
    
    def get_report_data(self):
        """Extract vendor ledger data"""
        AccountMoveLine = self.env['account.move.line']
        
        # DEBUG: Log what we're working with
        _logger.info("=" * 80)
        _logger.info("VENDOR LEDGER DEBUG")
        _logger.info(f"partner_ids field value: {self.partner_ids}")
        _logger.info(f"partner_ids length: {len(self.partner_ids)}")
        _logger.info(f"partner_ids IDs: {self.partner_ids.ids}")
        
        # Payable accounts domain
        account_domain = [
            '|',
            ('account_id.account_type', '=', 'liability_payable'),
            ('account_id.account_type', '=', 'payable'),
        ]
        
        # Determine which vendors to include
        # Check if partner_ids exists AND has records
        if self.partner_ids and len(self.partner_ids) > 0:
            # Specific vendors selected
            vendors = self.partner_ids
            _logger.info(f"Using SELECTED vendors: {vendors.mapped('name')}")
        else:
            # No vendors selected - get ALL vendors from the system
            vendors = self.env['res.partner'].search([
                ('supplier_rank', '>', 0)
            ], order='name')
            _logger.info(f"Using ALL vendors count: {len(vendors)}")
            _logger.info(f"Vendor names: {vendors.mapped('name')}")
        
        _logger.info("=" * 80)
        
        vendors_data = []
        
        for vendor in vendors.sorted('name'):
            # Get opening balance (before date_from)
            opening_lines = AccountMoveLine.search(account_domain + [
                ('partner_id', '=', vendor.id),
                ('date', '<', self.date_from),
                ('parent_state', '=', 'posted'),
            ])
            opening_balance = sum(opening_lines.mapped('balance'))
            
            # Get transactions in the period
            period_lines = AccountMoveLine.search(account_domain + [
                ('partner_id', '=', vendor.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted'),
            ], order='date asc, id asc')
            
            _logger.info(f"Vendor: {vendor.name} | Opening: {opening_balance} | Period lines: {len(period_lines)}")
            
            # Skip vendors with no opening balance AND no transactions in the period
            if not period_lines and opening_balance == 0:
                _logger.info(f"  -> SKIPPED (no data)")
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
            
            _logger.info(f"  -> INCLUDED (entries: {len(entries)})")
            
            vendors_data.append({
                'vendor_name': vendor.name,
                'vendor_id': vendor.id,
                'opening_balance': opening_balance,
                'entries': entries,
                'closing_balance': running_balance,
                'total_debit': sum(e['debit'] for e in entries),
                'total_credit': sum(e['credit'] for e in entries),
            })
        
        _logger.info(f"FINAL vendors_data count: {len(vendors_data)}")
        return vendors_data