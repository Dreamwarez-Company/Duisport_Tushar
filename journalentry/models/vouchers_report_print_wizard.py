# models/vouchers_report_print_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class VouchersReportPrintWizard(models.TransientModel):
    _name = 'vouchers.report.print.wizard'
    _description = 'Vouchers Report Print Wizard'
    
    report_id = fields.Many2one('vouchers.report', string='Report', required=True)
    report_name = fields.Char(string='Report Name', related='report_id.name')
    print_format = fields.Selection([
        ('pdf', 'PDF Format'),
        ('excel', 'Excel Format'),
        ('html', 'HTML Preview'),
    ], string='Print Format', default='pdf')
    
    include_summary = fields.Boolean(string='Include Summary', default=True)
    include_details = fields.Boolean(string='Include Details', default=True)
    include_filters = fields.Boolean(string='Include Filters Used', default=True)
    paper_size = fields.Selection([
        ('a4', 'A4'),
        ('letter', 'Letter'),
        ('legal', 'Legal'),
    ], string='Paper Size', default='a4')
    orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape'),
    ], string='Orientation', default='portrait')
    
    preview_data = fields.Html(string='Preview', compute='_compute_preview_data')
    
    @api.depends('report_id', 'print_format')
    def _compute_preview_data(self):
        for wizard in self:
            report = wizard.report_id
            
            # Build HTML content safely
            html_parts = []
            
            html_parts.append("""
            <div style="padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #333; border-bottom: 2px solid #007BFF; padding-bottom: 10px;">
                    Vouchers Report: %s
                </h2>
            """ % (report.name or ''))
            
            html_parts.append("""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #555;">Report Period</h3>
                    <p><strong>From:</strong> %s <strong>To:</strong> %s</p>
                    
                    <h3 style="color: #555;">Summary</h3>
                    <table style="width: 100%%; border-collapse: collapse; margin-bottom: 15px;">
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Debit</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">%.2f</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Credit</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">%.2f</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Balance</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">%.2f</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Total Vouchers</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">%s</td>
                        </tr>
                    </table>
                </div>
            """ % (
                report.date_from or '',
                report.date_to or '',
                report.total_debit or 0.0,
                report.total_credit or 0.0,
                report.total_balance or 0.0,
                report.total_vouchers or 0
            ))
            
            # Add sample lines table
            html_parts.append("""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #555;">Sample Data (First 3 entries)</h3>
                    <table style="width: 100%%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="padding: 8px; border: 1px solid #ddd;">Date</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Voucher No.</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Partner</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Debit</th>
                                <th style="padding: 8px; border: 1px solid #ddd;">Credit</th>
                            </tr>
                        </thead>
                        <tbody>
            """)
            
            # Add sample lines (first 3)
            lines = report.line_ids[:3]
            for line in lines:
                html_parts.append("""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;">%s</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">%s</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">%s</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">%.2f</td>
                        <td style="padding: 8px; border: 1px solid #ddd;">%.2f</td>
                    </tr>
                """ % (
                    line.accounting_date or '',
                    line.voucher_number or '',
                    line.partner_id.name if line.partner_id else '',
                    line.debit_amount or 0.0,
                    line.credit_amount or 0.0
                ))
            
            # Get selection values
            print_format_dict = dict(self._fields['print_format'].selection)
            paper_size_dict = dict(self._fields['paper_size'].selection)
            orientation_dict = dict(self._fields['orientation'].selection)
            
            html_parts.append("""
                        </tbody>
                    </table>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
                    <p><strong>Print Format:</strong> %s</p>
                    <p><strong>Paper Size:</strong> %s | <strong>Orientation:</strong> %s</p>
                    <p><em>Click "Print" to generate the full report</em></p>
                </div>
            </div>
            """ % (
                print_format_dict.get(wizard.print_format, ''),
                paper_size_dict.get(wizard.paper_size, ''),
                orientation_dict.get(wizard.orientation, '')
            ))
            
            # Join all HTML parts
            wizard.preview_data = ''.join(html_parts)
    
    # def action_print(self):
    #     """Execute the print action"""
    #     self.ensure_one()
        
    #     if self.print_format == 'pdf':
    #         # Return the PDF report action
    #         return self.env.ref('journalentry.report_vouchers').report_action(self.report_id)
        
    #     elif self.print_format == 'excel':
    #         # Export to Excel
    #         return self.report_id.action_export_excel()
        
    #     elif self.print_format == 'html':
    #         # Open HTML preview in new tab
    #         return {
    #             'type': 'ir.actions.act_url',
    #             'url': '/web/content/vouchers.report/%s/html_preview' % self.report_id.id,
    #             'target': 'new',
    #         }
    def action_print(self):
        """Execute the print action"""
        self.ensure_one()
        
        if self.print_format == 'pdf':
            try:
                # Try to get the report action
                report_action = self.env.ref('journalentry.report_vouchers')
                if report_action:
                    return report_action.report_action(self.report_id)
            except:
                # If report not found, create a simple one or show message
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'PDF Report',
                        'message': 'PDF report would be generated here. Please configure the report template.',
                        'type': 'info',
                        'sticky': False,
                    }
                }
        
        elif self.print_format == 'excel':
            # Export to Excel
            return self.report_id.action_export_excel()
        
        elif self.print_format == 'html':
            # Open HTML preview in new window
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/vouchers.report/%s/html_preview' % self.report_id.id,
                'target': 'new',
            }
    
    def action_close(self):
        """Close the wizard"""
        return {'type': 'ir.actions.act_window_close'}