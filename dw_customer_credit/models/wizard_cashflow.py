from odoo import fields, models, api
from odoo.exceptions import UserError
import json

class DwCashflowForecastWizard(models.TransientModel):
    _name = "dw.cashflow.forecast.wizard"
    _description = "Cash Flow Forecast Wizard"

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.context_today)
    
    # Fields to store and display lines
    cashflow_lines_json = fields.Text(string="Cash Flow Lines Data", default="[]")
    cashflow_lines_html = fields.Html(string="Cash Flow Lines", compute='_compute_cashflow_lines_html', store=False)
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Totals fields
    total_inflow = fields.Float(string="Total Inflow", compute='_compute_totals', store=False)
    total_outflow = fields.Float(string="Total Outflow", compute='_compute_totals', store=False)
    net_cash_flow = fields.Float(string="Net Cash Flow", compute='_compute_totals', store=False)

    def _compute_has_data(self):
        for wizard in self:
            wizard.has_data = bool(wizard.cashflow_lines_json and wizard.cashflow_lines_json != '[]')

    @api.depends('cashflow_lines_json')
    def _compute_cashflow_lines_html(self):
        for wizard in self:
            html_content = ""
            try:
                lines = json.loads(wizard.cashflow_lines_json or '[]')
                if lines:
                    # Start building HTML table
                    html_content = """
                    <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Date</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Description</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Inflow</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Outflow</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    total_inflow = 0
                    total_outflow = 0
                    
                    for line in lines:
                        inflow = line.get('inflow', 0)
                        outflow = line.get('outflow', 0)
                        total_inflow += inflow
                        total_outflow += outflow
                        
                        html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;">{line.get('date', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{line.get('description', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{inflow:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{outflow:.2f}</td>
                        </tr>
                        """
                    
                    # Add totals row
                    html_content += f"""
                        <tr style="border-top: 2px solid #000; font-weight: bold;">
                            <td colspan="2" style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total:</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_inflow:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_outflow:.2f}</td>
                        </tr>
                    """
                    
                    html_content += """
                        </tbody>
                    </table>
                    """
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.cashflow_lines_html = html_content

    @api.depends('cashflow_lines_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                lines = json.loads(wizard.cashflow_lines_json or '[]')
                wizard.total_inflow = sum(line.get('inflow', 0) for line in lines)
                wizard.total_outflow = sum(line.get('outflow', 0) for line in lines)
                wizard.net_cash_flow = wizard.total_inflow - wizard.total_outflow
            except:
                wizard.total_inflow = 0
                wizard.total_outflow = 0
                wizard.net_cash_flow = 0

    def action_generate_cashflow(self):
        """
        Generate cash flow lines and display them in the wizard
        """
        self.ensure_one()
        
        # Validate dates
        if self.start_date > self.end_date:
            raise UserError("Start date cannot be after end date.")
        
        # Get cash flow data
        lines_data = self._get_cashflow_lines()
        
        # Store as JSON
        self.cashflow_lines_json = json.dumps(lines_data)
        
        # Return action to refresh the view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_cashflow(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have lines to print
        if not self.cashflow_lines_json or self.cashflow_lines_json == '[]':
            raise UserError("Please generate cash flow data first using the 'Generate' button.")
        
        return self.env.ref('dw_customer_credit.action_report_cashflow').report_action(self)
    
    def _get_cashflow_lines(self):
        """
        Get actual cash flow data from the database.
        """
        self.ensure_one()
        lines = []
        
        # Add opening balance
        lines.append({
            'date': self.start_date.strftime('%Y-%m-%d') if self.start_date else '',
            'description': 'Opening Balance',
            'inflow': 0.0,
            'outflow': 0.0,
        })
        
        # Get customer payments (inflows)
        payments = self.env['account.payment'].search([
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ], order='date asc')
        
        for payment in payments:
            lines.append({
                'date': payment.date.strftime('%Y-%m-%d') if payment.date else '',
                'description': f"Payment from {payment.partner_id.name}",
                'inflow': float(payment.amount),
                'outflow': 0.0,
            })
        
        # Get vendor payments (outflows)
        vendor_payments = self.env['account.payment'].search([
            ('payment_type', '=', 'outbound'),
            ('state', '=', 'posted'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ], order='date asc')
        
        for payment in vendor_payments:
            lines.append({
                'date': payment.date.strftime('%Y-%m-%d') if payment.date else '',
                'description': f"Payment to {payment.partner_id.name}",
                'inflow': 0.0,
                'outflow': float(payment.amount),
            })
        
        # Add closing balance
        lines.append({
            'date': self.end_date.strftime('%Y-%m-%d') if self.end_date else '',
            'description': 'Closing Balance',
            'inflow': 0.0,
            'outflow': 0.0,
        })
        
        return lines
    
    def get_cashflow_lines(self):
        """Get parsed lines for report template"""
        self.ensure_one()
        try:
            return json.loads(self.cashflow_lines_json or '[]')
        except:
            return []