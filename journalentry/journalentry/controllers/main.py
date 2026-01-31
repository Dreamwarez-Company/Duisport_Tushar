from odoo import http, fields
from odoo.http import request
from datetime import datetime

class JournalEntryController(http.Controller):


    # Add this method to test the controller
    @http.route('/journalentry/test', type='http', auth='user')
    def test_route(self, **kwargs):
        return request.make_response("Controller is working!", headers=[('Content-Type', 'text/plain')])
    
    @http.route('/journalentry/vouchers_report/<int:report_id>/print', type='http', auth='user')
    def vouchers_report_print(self, report_id, **kwargs):
        report = request.env['vouchers.report'].browse(report_id)
        if not report.exists():
            return request.not_found()
        
        # Format current datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Vouchers Report - {report.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; border-bottom: 2px solid #007BFF; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 25px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                .summary-table {{ width: 50%; margin-bottom: 30px; }}
                .print-btn {{ 
                    padding: 12px 24px; 
                    margin: 20px 0; 
                    background: #007bff; 
                    color: white; 
                    border: none; 
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                }}
                .print-btn:hover {{ background: #0056b3; }}
                @media print {{ 
                    .no-print {{ display: none; }}
                    body {{ margin: 0; padding: 15px; }}
                }}
                .header-info {{ margin-bottom: 30px; }}
                .total-row {{ font-weight: bold; background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header-info">
                <h1>VOUCHERS REPORT</h1>
                <h2>{report.name}</h2>
                <p><strong>Period:</strong> {report.date_from} to {report.date_to}</p>
                <p><strong>Generated:</strong> {current_time}</p>
            </div>
            
            <div class="no-print">
                <button onclick="window.print()" class="print-btn">
                    🖨️ Print Report
                </button>
            </div>
            
            <div style="margin: 20px 0;">
                <h2>Summary</h2>
                <table class="summary-table">
                    <tr>
                        <td><strong>Total Debit:</strong></td>
                        <td style="text-align: right;">{report.total_debit:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Credit:</strong></td>
                        <td style="text-align: right;">{report.total_credit:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Balance:</strong></td>
                        <td style="text-align: right;">{report.total_balance:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Vouchers:</strong></td>
                        <td style="text-align: right;">{report.total_vouchers}</td>
                    </tr>
                </table>
            </div>
            
            <h2>Voucher Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Voucher No.</th>
                        <th>Partner</th>
                        <th>Journal</th>
                        <th>Type</th>
                        <th>Debit</th>
                        <th>Credit</th>
                        <th>Balance</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add all lines
        for line in report.line_ids:
            html += f"""
                    <tr>
                        <td>{line.accounting_date or ''}</td>
                        <td>{line.voucher_number or ''}</td>
                        <td>{line.partner_id.name if line.partner_id else ''}</td>
                        <td>{line.journal or ''}</td>
                        <td>{line.voucher_type or ''}</td>
                        <td style="text-align: right;">{line.debit_amount:,.2f}</td>
                        <td style="text-align: right;">{line.credit_amount:,.2f}</td>
                        <td style="text-align: right;">{line.balance_amount:,.2f}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="5"><strong>TOTALS</strong></td>
                        <td style="text-align: right;"><strong>{report.total_debit:,.2f}</strong></td>
                        <td style="text-align: right;"><strong>{report.total_credit:,.2f}</strong></td>
                        <td style="text-align: right;"><strong>{report.total_balance:,.2f}</strong></td>
                    </tr>
                </tfoot>
            </table>
            
            <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #888; text-align: center;">
                <p>End of Report</p>
                <p>Page generated by Odoo Vouchers Report Module</p>
            </div>
            
            <script>
                // Auto-print option (uncomment if you want auto-print)
                // window.onload = function() {{
                //     window.print();
                // }};
            </script>
        </body>
        </html>
        """
        
        return request.make_response(html, headers=[('Content-Type', 'text/html')])