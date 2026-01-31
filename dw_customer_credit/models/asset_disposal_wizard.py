from odoo import fields, models, api
from odoo.exceptions import UserError
import json

class AssetDisposalWizard(models.TransientModel):
    _name = "asset.disposal.wizard"
    _description = "Asset Disposal Report Wizard"

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string="Journal")
    asset_category_id = fields.Many2one('account.asset.category', string="Asset Category")
    
    # New fields for data storage and display
    disposal_data_json = fields.Text(string="Disposal Data", default="[]")
    disposal_data_html = fields.Html(string="Disposal Records", compute='_compute_disposal_data_html', store=False)
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Summary fields
    total_disposal_amount = fields.Float(string="Total Disposal Amount", compute='_compute_totals', store=False)
    total_records = fields.Integer(string="Total Records", compute='_compute_totals', store=False)
    
    def _compute_has_data(self):
        for wizard in self:
            wizard.has_data = bool(wizard.disposal_data_json and wizard.disposal_data_json != '[]')
    
    @api.depends('disposal_data_json')
    def _compute_disposal_data_html(self):
        for wizard in self:
            html_content = ""
            try:
                data = json.loads(wizard.disposal_data_json or '[]')
                if data:
                    # Start building HTML table
                    html_content = """
                    <div class="alert alert-info" style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                        <strong>Asset Disposal Report Summary:</strong> {count} record(s) found<br>
                        <strong>Total Disposal Amount:</strong> {total_amount:.2f}
                    </div>
                    
                    <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="background-color: #2c3e50; color: white;">
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Date</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Asset Name</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Category</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Journal</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Journal Entry</th>
                                <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                    """.format(count=len(data), total_amount=wizard.total_disposal_amount)
                    
                    for record in data:
                        amount = record.get('disposal_amount', 0)
                        
                        html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;">{record.get('date', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{record.get('asset_name', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{record.get('asset_category', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{record.get('journal', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{record.get('journal_entry', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{amount:.2f}</td>
                        </tr>
                        """
                    
                    html_content += """
                        </tbody>
                    </table>
                    """
                else:
                    html_content = """
                    <div class="alert alert-warning" style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px;">
                        <strong>No disposal records found!</strong><br>
                        No asset disposal records found for the selected period and filters. Please adjust your criteria and try again.
                    </div>
                    """
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.disposal_data_html = html_content
    
    @api.depends('disposal_data_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                data = json.loads(wizard.disposal_data_json or '[]')
                total_amount = sum(record.get('disposal_amount', 0) for record in data)
                wizard.total_disposal_amount = total_amount
                wizard.total_records = len(data)
            except:
                wizard.total_disposal_amount = 0
                wizard.total_records = 0
    
    def action_generate_disposal_data(self):
        """
        Generate asset disposal data and display in wizard
        """
        self.ensure_one()
        
        # Validate dates
        if self.start_date > self.end_date:
            raise UserError("Start Date cannot be after End Date.")
        
        # Get disposal data
        disposal_data = self._get_disposal_lines()
        
        # Store as JSON
        self.disposal_data_json = json.dumps(disposal_data)
        
        # Return to refresh view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_print_asset_disposal(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have data to print
        if not self.disposal_data_json or self.disposal_data_json == '[]':
            raise UserError("Please generate disposal data first using the 'Generate' button.")
        
        return self.env.ref('dw_customer_credit.action_report_asset_disposal').report_action(self)
    
    def _get_disposal_lines(self):
        """
        Get asset disposal data from the database.
        This version looks for ANY moves in disposal journals and tries to link them to assets.
        """
        lines = []
        
        # Get disposal journals (MISC, STJ, EXCH, CABA)
        disposal_journals = self.env['account.journal'].search([
            ('code', 'in', ['MISC', 'STJ', 'EXCH', 'CABA'])
        ])
        
        # Build search domain
        move_domain = [
            ('state', '=', 'posted'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ]
        
        if self.journal_id:
            move_domain.append(('journal_id', '=', self.journal_id.id))
        else:
            move_domain.append(('journal_id', 'in', disposal_journals.ids))
        
        # Search for moves
        moves = self.env['account.move'].search(move_domain)
        
        for move in moves:
            # METHOD 1: Check if move name or ref contains asset/disposal info
            asset = None
            
            # Try to extract asset name from move lines description
            for line in move.line_ids:
                line_name = line.name or ''
                
                # Look for patterns like "Disposal of [Asset Name]" or asset names
                if 'Disposal' in line_name or 'disposal' in line_name.lower():
                    # Try to extract asset name
                    import re
                    match = re.search(r'Disposal of (.+)', line_name, re.IGNORECASE)
                    if match:
                        asset_name = match.group(1).strip()
                        # Search for asset by name
                        asset = self.env['account.asset.asset'].search([
                            ('name', 'ilike', asset_name)
                        ], limit=1)
                
                # If no asset found by name, check if line has asset_id
                if not asset and hasattr(line, 'asset_id') and line.asset_id:
                    asset = line.asset_id
            
            # METHOD 2: Check depreciation lines
            if not asset:
                dep_lines = self.env['account.asset.depreciation.line'].search([
                    ('move_id', '=', move.id),
                    ('asset_id', '!=', False),
                ], limit=1)
                if dep_lines:
                    asset = dep_lines[0].asset_id
            
            # METHOD 3: Try to find asset by matching amounts
            if not asset:
                # Look for moves where total amount matches an asset's residual value
                move_total = abs(sum(move.line_ids.mapped('balance'))) / 2
                
                # Search for assets with similar residual value
                assets = self.env['account.asset.asset'].search([
                    ('state', 'in', ['open', 'close']),
                    ('value_residual', '>', 0),
                ])
                
                for a in assets:
                    # Check if move amount is close to asset residual value
                    if abs(move_total - a.value_residual) < 1:  # Within 1 currency unit
                        asset = a
                        break
            
            # If we found an asset, add it to report
            if asset:
                # Calculate disposal amount (use the largest line amount)
                disposal_amount = 0
                for line in move.line_ids:
                    if abs(line.balance) > disposal_amount:
                        disposal_amount = abs(line.balance)
                
                # Apply category filter
                if self.asset_category_id and asset.category_id.id != self.asset_category_id.id:
                    continue
                
                lines.append({
                    'date': move.date.strftime('%Y-%m-%d') if move.date else '',
                    'asset_name': asset.name or '',
                    'asset_category': asset.category_id.name or '',
                    'journal': move.journal_id.name,
                    'journal_entry': move.name,
                    'disposal_amount': disposal_amount,
                    'partner': move.partner_id.name if move.partner_id else '',
                    'description': move.ref or f"Disposal of {asset.name}",
                })
            else:
                # No asset found, but this is still a disposal journal entry
                # Add it anyway with generic info
                disposal_amount = 0
                for line in move.line_ids:
                    if abs(line.balance) > disposal_amount:
                        disposal_amount = abs(line.balance)
                
                lines.append({
                    'date': move.date.strftime('%Y-%m-%d') if move.date else '',
                    'asset_name': 'Unknown Asset',
                    'asset_category': 'Unknown',
                    'journal': move.journal_id.name,
                    'journal_entry': move.name,
                    'disposal_amount': disposal_amount,
                    'partner': move.partner_id.name if move.partner_id else '',
                    'description': move.ref or 'Asset Disposal Entry',
                })
        
        # Sort by date
        lines.sort(key=lambda x: x['date'])
        
        return lines
    
    def _get_total_disposal_amount(self):
        """
        Calculate total disposal amount for the period.
        """
        try:
            data = json.loads(self.disposal_data_json or '[]')
            total = sum(record.get('disposal_amount', 0) for record in data)
            return total
        except:
            return 0.0
    
    def get_disposal_lines(self):
        """Get parsed lines for report template"""
        self.ensure_one()
        try:
            return json.loads(self.disposal_data_json or '[]')
        except:
            return []