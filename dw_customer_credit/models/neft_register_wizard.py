from odoo import fields, models, api
from odoo.tools import format_date
from odoo.exceptions import UserError
import json

class NeftRegisterWizard(models.TransientModel):
    _name = "neft.register.wizard"
    _description = "NEFT Register Wizard"
    
    date_from = fields.Date(string="From Date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To Date", required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string="Bank Journal", 
                                 domain=[('type', 'in', ['bank', 'cash'])])
    include_vendor_payments = fields.Boolean(string="Include Vendor Payments", default=True)
    include_transfers = fields.Boolean(string="Include Internal Transfers", default=True)
    include_customer_payments = fields.Boolean(string="Include Customer Payments", default=False)
    
    # New fields for data storage and display
    neft_data_json = fields.Text(string="NEFT Data", default="[]")
    neft_data_html = fields.Html(string="NEFT Transactions", compute='_compute_neft_data_html', store=False)
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Summary fields
    total_amount = fields.Float(string="Total Amount", compute='_compute_totals', store=False)
    vendor_count = fields.Integer(string="Vendor Payments", compute='_compute_totals', store=False)
    transfer_count = fields.Integer(string="Internal Transfers", compute='_compute_totals', store=False)
    customer_count = fields.Integer(string="Customer Payments", compute='_compute_totals', store=False)
    
    def _compute_has_data(self):
        for wizard in self:
            wizard.has_data = bool(wizard.neft_data_json and wizard.neft_data_json != '[]')
    
    @api.depends('neft_data_json')
    def _compute_neft_data_html(self):
        for wizard in self:
            html_content = ""
            try:
                transactions = json.loads(wizard.neft_data_json or '[]')
                if transactions:
                    # Start building HTML table
                    html_content = """
                    <div class="alert alert-info" style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                        <strong>Report Type:</strong> Outgoing Payments & Transfers<br>
                        <strong>Transactions Found:</strong> {count} transaction(s)
                    </div>
                    
                    <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="background-color: #4a6fa5; color: white;">
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Date</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Voucher No.</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Type</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">From Account</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">To Account</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                    """.format(count=len(transactions))
                    
                    total_amount = 0
                    
                    for t in transactions:
                        amount = t.get('amount', 0)
                        total_amount += amount
                        
                        # Determine row class
                        payment_type = t.get('payment_type', '')
                        row_class = ""
                        if payment_type == 'outbound':
                            row_class = "style='background-color: #fff3f3;'"
                        elif payment_type == 'transfer':
                            row_class = "style='background-color: #e8f4f8;'"
                        elif payment_type == 'inbound':
                            row_class = "style='background-color: #f0fff0;'"
                        
                        # Format amount display
                        amount_display = ""
                        if amount < 0:
                            amount_display = f"<span style='color: red; font-weight: bold;'>({abs(amount):.2f})</span>"
                        else:
                            amount_display = f"<span style='color: green; font-weight: bold;'>{amount:.2f}</span>"
                        
                        html_content += f"""
                        <tr {row_class}>
                            <td style="padding: 8px; border: 1px solid #ddd;">{t.get('date', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{t.get('voucher_no', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{t.get('transaction_type', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{t.get('from_account', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{t.get('to_account', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{amount_display}</td>
                        </tr>
                        """
                    
                    # Add totals row
                    total_display = ""
                    if total_amount < 0:
                        total_display = f"<span style='color: red; font-weight: bold;'>({abs(total_amount):.2f})</span>"
                    else:
                        total_display = f"<span style='color: green; font-weight: bold;'>{total_amount:.2f}</span>"
                    
                    html_content += f"""
                        <tr style="border-top: 2px solid #4a6fa5; font-weight: bold; background-color: #e8f4f8;">
                            <td colspan="5" style="padding: 8px; border: 1px solid #ddd; text-align: right;">Net Cash Flow:</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_display}</td>
                        </tr>
                        </tbody>
                    </table>
                    """
                else:
                    html_content = """
                    <div class="alert alert-warning" style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px;">
                        <strong>No transactions found!</strong><br>
                        No outgoing payment transactions found for the selected criteria. Please adjust your filters and try again.
                    </div>
                    """
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.neft_data_html = html_content
    
    @api.depends('neft_data_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                transactions = json.loads(wizard.neft_data_json or '[]')
                total_amount = 0
                vendor_count = 0
                transfer_count = 0
                customer_count = 0
                
                for t in transactions:
                    amount = t.get('amount', 0)
                    total_amount += amount
                    
                    payment_type = t.get('payment_type', '')
                    if payment_type == 'outbound':
                        vendor_count += 1
                    elif payment_type == 'transfer':
                        transfer_count += 1
                    elif payment_type == 'inbound':
                        customer_count += 1
                
                wizard.total_amount = total_amount
                wizard.vendor_count = vendor_count
                wizard.transfer_count = transfer_count
                wizard.customer_count = customer_count
            except:
                wizard.total_amount = 0
                wizard.vendor_count = 0
                wizard.transfer_count = 0
                wizard.customer_count = 0
    
    def action_generate_neft_data(self):
        """
        Generate NEFT data and display in wizard
        """
        self.ensure_one()
        
        # Validate dates
        if self.date_from > self.date_to:
            raise UserError("From Date cannot be after To Date.")
        
        # Get NEFT transactions data
        transactions_data = self._get_neft_transactions()
        
        # Store as JSON
        self.neft_data_json = json.dumps(transactions_data)
        
        # Return to refresh view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_print_neft_register(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have data to print
        if not self.neft_data_json or self.neft_data_json == '[]':
            raise UserError("Please generate NEFT data first using the 'Generate' button.")
        
        return self.env.ref('dw_customer_credit.action_report_neft_register').report_action(self)
    
    def _get_neft_transactions(self):
        """
        Method to get only OUTGOING bank transactions (vendor payments and transfers).
        Excludes customer payments (incoming money).
        """
        # Build domain based on selected options
        payment_types = []
        
        # Note: 'outbound' = money going OUT (vendor payments)
        #       'transfer' = money transferred between accounts  
        #       'inbound' = money coming IN (customer payments) - we exclude this
        
        if self.include_vendor_payments:
            payment_types.append('outbound')
        if self.include_transfers:
            payment_types.append('transfer')
        if self.include_customer_payments:
            payment_types.append('inbound')
        
        if not payment_types:
            return []
        
        domain = [
            ('payment_type', 'in', payment_types),
            ('state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id.type', 'in', ['bank', 'cash']),
        ]
        
        if self.journal_id:
            domain.append(('journal_id', '=', self.journal_id.id))
        
        # Search for payments
        payments = self.env['account.payment'].search(domain, order='date asc, id asc')
        
        lines = []
        for payment in payments:
            # Determine from/to accounts based on payment type
            if payment.payment_type == 'transfer':
                from_account = payment.journal_id.name
                to_account = payment.destination_journal_id.name if payment.destination_journal_id else ''
                amount = payment.amount  # Positive for transfers
            elif payment.payment_type == 'outbound':
                from_account = payment.journal_id.name
                to_account = payment.partner_id.name if payment.partner_id else 'Vendor'
                amount = -payment.amount  # Negative for vendor payments (money going out)
            elif payment.payment_type == 'inbound':
                from_account = payment.partner_id.name if payment.partner_id else 'Customer'
                to_account = payment.journal_id.name
                amount = payment.amount  # Positive for customer payments (money coming in)
            else:
                from_account = payment.journal_id.name
                to_account = ''
                amount = payment.amount
            
            # Format the transaction type
            if payment.payment_type == 'transfer':
                trans_type = 'Internal Transfer'
            elif payment.payment_type == 'outbound':
                trans_type = 'Vendor Payment'
            elif payment.payment_type == 'inbound':
                trans_type = 'Customer Payment'
            else:
                trans_type = 'Other'
            
            # Format date
            formatted_date = format_date(self.env, payment.date, date_format='dd-MM-yyyy')
            
            lines.append({
                'date': formatted_date,
                'voucher_no': payment.name or '',
                'transaction_type': trans_type,
                'from_account': from_account or '',
                'to_account': to_account or '',
                'amount': amount,
                'reference': payment.ref or '-',
                'remarks': payment.narration or '-',
                'partner': payment.partner_id.name if payment.partner_id else '',
                'payment_type': payment.payment_type,
            })
        
        return lines
    
    def get_neft_lines(self):
        """Get parsed lines for report template"""
        self.ensure_one()
        try:
            return json.loads(self.neft_data_json or '[]')
        except:
            return []