from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import AccessError, UserError
import json

class CWIPReportWizard(models.TransientModel):
    _name = "cwip.report.wizard"
    _description = "CWIP Report Wizard"
    _inherit = ['mail.thread']
    
    date_as_of = fields.Date(string="As of Date", required=True, default=fields.Date.context_today)
    category_id = fields.Many2one('account.asset.category', string="Asset Category")
    partner_id = fields.Many2one('res.partner', string="Vendor/Customer")
    project_ref = fields.Char(string="Project/Contract Reference")
    location = fields.Char(string="Location")
    
    status = fields.Selection([
        ('draft', 'Draft Assets'),
        ('open', 'Running Assets'),
        ('all', 'All Status'),
    ], string="Status", default='open')
    
    # New fields for data storage and display
    cwip_data_json = fields.Text(string="CWIP Data", default="[]")
    cwip_data_html = fields.Html(string="CWIP Assets", compute='_compute_cwip_data_html', store=False)
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Summary fields
    total_cwip_value = fields.Float(string="Total CWIP Value", compute='_compute_totals', store=False)
    total_assets = fields.Integer(string="Total Assets", compute='_compute_totals', store=False)
    draft_count = fields.Integer(string="Draft Assets", compute='_compute_totals', store=False)
    open_count = fields.Integer(string="Running Assets", compute='_compute_totals', store=False)
    
    def _compute_has_data(self):
        for wizard in self:
            wizard.has_data = bool(wizard.cwip_data_json and wizard.cwip_data_json != '[]')
    
    @api.depends('cwip_data_json')
    def _compute_cwip_data_html(self):
        for wizard in self:
            html_content = ""
            try:
                data = json.loads(wizard.cwip_data_json or '[]')
                if data:
                    # Start building HTML table
                    html_content = """
                    <div class="alert alert-info" style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                        <strong>CWIP Report Summary:</strong> {count} asset(s) found<br>
                        <strong>Total CWIP Value:</strong> {total_value:.2f}
                    </div>
                    
                    <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="background-color: #2c3e50; color: white;">
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Asset Code</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Asset Name</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Category</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Acq. Date</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">CWIP Value</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                    """.format(count=len(data), total_value=wizard.total_cwip_value)
                    
                    for asset in data:
                        cwip_value = asset.get('cwip_value', 0)
                        cwip_status = asset.get('cwip_status', '')
                        
                        # Determine status color
                        status_color = ""
                        if cwip_status == 'In Progress':
                            status_color = "background-color: #fff3cd; color: #856404;"
                        elif cwip_status == 'Not Started':
                            status_color = "background-color: #f8d7da; color: #721c24;"
                        elif cwip_status == 'Depreciation Started':
                            status_color = "background-color: #d1ecf1; color: #0c5460;"
                        else:
                            status_color = "background-color: #f0f0f0; color: #333;"
                        
                        html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;">{asset.get('asset_code', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{asset.get('asset_name', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{asset.get('category', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{asset.get('acquisition_date', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cwip_value:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; {status_color}">{cwip_status}</td>
                        </tr>
                        """
                    
                    html_content += """
                        </tbody>
                    </table>
                    """
                else:
                    html_content = """
                    <div class="alert alert-warning" style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px;">
                        <strong>No CWIP assets found!</strong><br>
                        No capital work in progress assets found for the selected criteria. Please adjust your filters and try again.
                    </div>
                    """
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.cwip_data_html = html_content
    
    @api.depends('cwip_data_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                data = json.loads(wizard.cwip_data_json or '[]')
                total_cwip_value = 0
                draft_count = 0
                open_count = 0
                
                for asset in data:
                    cwip_value = asset.get('cwip_value', 0)
                    total_cwip_value += cwip_value
                    
                    asset_state = asset.get('asset_state', '')
                    if asset_state == 'draft':
                        draft_count += 1
                    elif asset_state == 'open':
                        open_count += 1
                
                wizard.total_cwip_value = total_cwip_value
                wizard.total_assets = len(data)
                wizard.draft_count = draft_count
                wizard.open_count = open_count
            except:
                wizard.total_cwip_value = 0
                wizard.total_assets = 0
                wizard.draft_count = 0
                wizard.open_count = 0
    
    def action_generate_cwip_data(self):
        """
        Generate CWIP data and display in wizard
        """
        self.ensure_one()
        
        # Get CWIP data
        cwip_data = self._get_cwip_data()
        
        # Store as JSON
        self.cwip_data_json = json.dumps(cwip_data.get('lines', []))
        
        # Return to refresh view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_print_cwip_report(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have data to print
        if not self.cwip_data_json or self.cwip_data_json == '[]':
            raise UserError("Please generate CWIP data first using the 'Generate' button.")
        
        return self.env.ref('dw_customer_credit.action_report_cwip_report').report_action(self)
    
    def _get_cwip_data(self):
        """
        Method to get Capital Work in Progress data.
        CWIP typically includes assets that are not yet completed/commissioned.
        """
        # Build search domain for CWIP assets
        domain = []
        
        # Add status filter
        if self.status and self.status != 'all':
            domain.append(('state', '=', self.status))
        else:
            # Default to include both draft and running assets for CWIP
            domain.append(('state', 'in', ['draft', 'open']))
        
        # Add category filter if selected
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        
        # Add partner filter if selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        # Search for assets
        assets = self.env['account.asset.asset'].search(domain, order='category_id, date, name')
        
        lines = []
        
        for asset in assets:
            has_depreciation = bool(asset.depreciation_line_ids)
            cwip_value = asset.value or 0.0
            
            # Skip assets with zero value
            if cwip_value <= 0:
                continue
            
            # Determine asset category
            asset_category = asset.category_id.name if asset.category_id else 'Uncategorized'
            
            # Get vendor/partner
            vendor = asset.partner_id.name if asset.partner_id else ''
            
            # Get acquisition date
            acquisition_date = asset.date
            
            # Calculate days since acquisition
            days_since_acquisition = 0
            if acquisition_date:
                delta = fields.Date.from_string(self.date_as_of) - acquisition_date
                days_since_acquisition = delta.days if delta.days > 0 else 0
            
            # Get invoice reference if available
            invoice_ref = asset.invoice_id.name if asset.invoice_id else ''
            
            # Determine CWIP status based on asset state and depreciation
            if asset.state == 'draft':
                cwip_status = 'Not Started'
            elif asset.state == 'open' and not has_depreciation:
                cwip_status = 'In Progress'
            elif asset.state == 'open' and has_depreciation:
                cwip_status = 'Depreciation Started'
            else:
                cwip_status = 'Completed'
            
            # Get description/notes
            description = asset.note or ''
            
            lines.append({
                'asset_code': asset.code or f"AST-{asset.id:04d}",
                'asset_name': asset.name,
                'category': asset_category,
                'acquisition_date': acquisition_date.strftime('%Y-%m-%d') if acquisition_date else '',
                'cwip_value': cwip_value,
                'vendor': vendor,
                'invoice_ref': invoice_ref,
                'days_since_acquisition': days_since_acquisition,
                'cwip_status': cwip_status,
                'description': description,
                'asset_state': asset.state,
                'has_depreciation': has_depreciation,
                'asset_id': asset.id,
            })
        
        # If no CWIP data found
        if not lines:
            lines = self._get_sample_cwip_data()
        
        total_cwip_value = sum(line.get('cwip_value', 0) for line in lines)
        
        return {
            'lines': lines,
            'total_cwip_value': total_cwip_value,
            'total_assets': len(lines),
            'date_as_of': self.date_as_of,
        }
    
    def _get_sample_cwip_data(self):
        """
        Fallback method to return sample CWIP data.
        """
        today = fields.Date.today()
        return [{
            'asset_code': 'NO-CWIP-FOUND',
            'asset_name': 'No Capital Work in Progress Found',
            'category': 'Information',
            'acquisition_date': today.strftime('%Y-%m-%d'),
            'cwip_value': 0.00,
            'vendor': 'N/A',
            'invoice_ref': '',
            'days_since_acquisition': 0,
            'cwip_status': 'No Data',
            'description': 'Please create assets with draft or running status',
            'asset_state': 'draft',
            'has_depreciation': False,
            'asset_id': 0,
        }]
    
    def get_cwip_lines(self):
        """Get parsed lines for report template"""
        self.ensure_one()
        try:
            return json.loads(self.cwip_data_json or '[]')
        except:
            return []