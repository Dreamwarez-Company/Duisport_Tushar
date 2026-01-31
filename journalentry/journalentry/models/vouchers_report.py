# models/vouchers_report.py
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class VouchersReport(models.Model):
    _name = 'vouchers.report'
    _description = 'Vouchers Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Report Name', required=True, default=lambda self: _('New'))
    date_from = fields.Date(string='From Date', required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.today)
    journal_id = fields.Many2one('account.journal', string='Journal')
    voucher_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('payment', 'Payment'),
        ('contra', 'Contra'),
        ('journal', 'Journal')
    ], string='Voucher Type')
    partner_id = fields.Many2one('res.partner', string='Partner')
    mode = fields.Char(string='Mode')
    form_status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Form Status')
    
    # Filter fields
    filter_by_account = fields.Char(string='Account Filter')
    filter_by_partner = fields.Char(string='Partner Filter')
    filter_by_amount_range = fields.Char(string='Amount Range')
    show_only_unbalanced = fields.Boolean(string='Show Only Unbalanced')
    group_by_account = fields.Boolean(string='Group by Account')
    group_by_partner = fields.Boolean(string='Group by Partner')
    group_by_voucher_type = fields.Boolean(string='Group by Voucher Type')
    include_drafts = fields.Boolean(string='Include Draft Vouchers')
    
    # Summary fields
    total_debit = fields.Float(string='Total Debit', readonly=True)
    total_credit = fields.Float(string='Total Credit', readonly=True)
    total_balance = fields.Float(string='Total Balance', readonly=True)
    total_vouchers = fields.Integer(string='Total Vouchers', readonly=True)
    cash_vouchers = fields.Integer(string='Cash Vouchers', readonly=True)
    bank_vouchers = fields.Integer(string='Bank Vouchers', readonly=True)
    journal_vouchers = fields.Integer(string='Journal Vouchers', readonly=True)
    contra_vouchers = fields.Integer(string='Contra Vouchers', readonly=True)
    
    # Lines
    line_ids = fields.One2many('vouchers.report.line', 'report_id', string='Voucher Lines')
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string='Status', default='draft', tracking=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('vouchers.report') or _('New')
        return super(VouchersReport, self).create(vals)
    
    def action_generate_report(self):
        # Logic to generate voucher report lines
        for report in self:
            # Clear existing lines
            report.line_ids.unlink()
            
            # Build domain for account moves
            domain = [
                ('date', '>=', report.date_from),
                ('date', '<=', report.date_to),
            ]
            
            if report.journal_id:
                domain.append(('journal_id', '=', report.journal_id.id))
            
            if report.voucher_type:
                domain.append(('voucher_type', '=', report.voucher_type))
            
            if report.partner_id:
                domain.append(('partner_id', '=', report.partner_id.id))
            
            if not report.include_drafts:
                domain.append(('state', '=', 'posted'))
            
            # Fetch moves
            moves = self.env['account.move'].search(domain)
            
            # Create report lines
            for move in moves:
                for line in move.line_ids:
                    self.env['vouchers.report.line'].create({
                        'report_id': report.id,
                        'accounting_date': move.date,
                        'voucher_number': move.name,
                        'partner_id': move.partner_id.id,
                        'journal': move.journal_id.name,
                        'voucher_type': move.voucher_type,
                        'debit_amount': line.debit,
                        'credit_amount': line.credit,
                        'balance_amount': line.balance,
                        'memo': line.name,
                    })
            
            # Calculate totals
            report._calculate_totals()
            
            report.state = 'confirmed'
    

    # In your vouchers_report.py file, update the action_print_report method:
    # def action_print_report(self):
    #     """Print report as HTML page"""
    #     if self.state == 'draft':
    #         self.action_generate_report()
        
    #     # Open HTML page in new tab that can be printed
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/journalentry/vouchers_report/{self.id}/print',
    #         'target': 'new',
    #     }
    
    def action_print_report(self):
        """Print report - simple HTML version"""
        if self.state == 'draft':
            self.action_generate_report()
        
        # Generate HTML content directly
        html_content = self._generate_print_html()
        
        # Create attachment
        import base64
        attachment = self.env['ir.attachment'].create({
            'name': f'Vouchers_Report_{self.name}.html',
            'type': 'binary',
            'datas': base64.b64encode(html_content.encode('utf-8')),
            'res_model': 'vouchers.report',
            'res_id': self.id,
            'mimetype': 'text/html'
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _generate_print_html(self):
        """Generate HTML for printing"""
        from datetime import datetime
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Vouchers Report - {self.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; border-bottom: 2px solid #007BFF; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 25px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                .print-btn {{ 
                    padding: 10px 20px; 
                    margin: 20px 0; 
                    background: #007bff; 
                    color: white; 
                    border: none; 
                    border-radius: 4px;
                    cursor: pointer;
                }}
                .print-btn:hover {{ background: #0056b3; }}
                @media print {{ 
                    .no-print {{ display: none; }}
                    body {{ margin: 0; }}
                }}
            </style>
        </head>
        <body>
            <div class="no-print">
                <button onclick="window.print()" class="print-btn">🖨️ Print Report</button>
                <button onclick="window.close()" class="print-btn" style="background: #6c757d; margin-left: 10px;">✖ Close</button>
            </div>
            
            <h1>VOUCHERS REPORT</h1>
            <h2>{self.name}</h2>
            <p><strong>Period:</strong> {self.date_from} to {self.date_to}</p>
            <p><strong>Generated:</strong> {current_time}</p>
            
            <h2>Summary</h2>
            <table style="width: 50%;">
                <tr>
                    <td><strong>Total Debit:</strong></td>
                    <td style="text-align: right;">{self.total_debit:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Total Credit:</strong></td>
                    <td style="text-align: right;">{self.total_credit:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Total Balance:</strong></td>
                    <td style="text-align: right;">{self.total_balance:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Total Vouchers:</strong></td>
                    <td style="text-align: right;">{self.total_vouchers}</td>
                </tr>
            </table>
            
            <h2>Voucher Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Voucher No.</th>
                        <th>Partner</th>
                        <th>Type</th>
                        <th>Debit</th>
                        <th>Credit</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for line in self.line_ids:
            html += f"""
                    <tr>
                        <td>{line.accounting_date or ''}</td>
                        <td>{line.voucher_number or ''}</td>
                        <td>{line.partner_id.name if line.partner_id else ''}</td>
                        <td>{line.voucher_type or ''}</td>
                        <td style="text-align: right;">{line.debit_amount:,.2f}</td>
                        <td style="text-align: right;">{line.credit_amount:,.2f}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            
            <div style="margin-top: 50px; font-size: 12px; color: #666; text-align: center;">
                <p>--- End of Report ---</p>
            </div>
            
            <script>
                // Optional: Auto-print after 1 second
                setTimeout(function() {{
                    // window.print();
                }}, 1000);
            </script>
        </body>
        </html>
        """
        
        return html

    def action_export_excel(self):
        # Logic to export to Excel
        return {
            'type': 'ir.actions.act_url',
            'url': '/journalentry/export_vouchers_excel/%s' % self.id,
            'target': 'new',
        }
    
    def action_reset_to_draft(self):
        self.state = 'draft'
    
    def _calculate_totals(self):
        for report in self:
            report.total_debit = sum(report.line_ids.mapped('debit_amount'))
            report.total_credit = sum(report.line_ids.mapped('credit_amount'))
            report.total_balance = report.total_debit - report.total_credit
            report.total_vouchers = len(set(report.line_ids.mapped('voucher_number')))
            # Calculate voucher type counts
            report.cash_vouchers = len(report.line_ids.filtered(lambda x: x.voucher_type == 'receipt'))
            report.bank_vouchers = len(report.line_ids.filtered(lambda x: x.voucher_type == 'payment'))
            report.journal_vouchers = len(report.line_ids.filtered(lambda x: x.voucher_type == 'journal'))
            report.contra_vouchers = len(report.line_ids.filtered(lambda x: x.voucher_type == 'contra'))


class VouchersReportLine(models.Model):
    _name = 'vouchers.report.line'
    _description = 'Vouchers Report Line'
    
    report_id = fields.Many2one('vouchers.report', string='Report', ondelete='cascade')
    accounting_date = fields.Date(string='Date')
    voucher_number = fields.Char(string='Voucher No.')
    partner_id = fields.Many2one('res.partner', string='Partner')
    journal = fields.Char(string='Journal')
    voucher_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('payment', 'Payment'),
        ('contra', 'Contra'),
        ('journal', 'Journal')
    ], string='Voucher Type')
    debit_amount = fields.Float(string='Debit')
    credit_amount = fields.Float(string='Credit')
    balance_amount = fields.Float(string='Balance')
    memo = fields.Char(string='Memo')

