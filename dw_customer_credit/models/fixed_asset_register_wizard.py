from odoo import fields, models, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessError, UserError
import json

class FixedAssetRegisterWizard(models.TransientModel):
    _name = "fixed.asset.register.wizard"
    _description = "Fixed Asset Register Wizard"
    _inherit = ['mail.thread']

    # ============ NEW FIELDS ============
    # JSON storage for asset data
    asset_lines_json = fields.Text(string="Asset Lines Data", default="[]")
    
    # HTML display field for wizard
    asset_lines_html = fields.Html(string="Asset Lines", compute='_compute_asset_lines_html', store=False)
    
    # Boolean to check if data exists
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Summary fields
    total_assets = fields.Integer(string="Total Assets", compute='_compute_totals', store=False)
    total_original_value = fields.Float(string="Total Original Value", compute='_compute_totals', store=False)
    total_depreciation = fields.Float(string="Total Depreciation", compute='_compute_totals', store=False)
    total_net_value = fields.Float(string="Total Net Value", compute='_compute_totals', store=False)
    # ============ END NEW FIELDS ============

    # Security - allow all users to read, restrict create/write
    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        if operation == 'read':
            return True
        if operation in ('create', 'write', 'unlink'):
            # Only allow accounting users or managers
            if self.env.user.has_group('account.group_account_user') or \
               self.env.user.has_group('base.group_system'):
                return True
            if raise_exception:
                raise AccessError(_("You don't have permission to create asset reports."))
            return False
        return super().check_access_rights(operation, raise_exception)

    # Add automatic access control
    @api.model
    def _check_access(self):
        """Basic access control for the wizard"""
        if not self.env.user.has_group('base.group_user'):
            raise AccessError(_("You need to be logged in to access this feature."))
        return True
    
    # ============ MAIN FIELDS ============
    date_as_of = fields.Date(string="As of Date", required=True, default=fields.Date.context_today)
    
    # Update status filter
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('all', 'All Status'),
    ], string="Status", default='open')
    
    # Add asset category filter
    category_id = fields.Many2one(
        'account.asset.category', 
        string="Asset Category",
        help="Filter by specific asset category"
    )
    
    # Add partner filter
    partner_id = fields.Many2one(
        'res.partner',
        string="Vendor/Customer",
        help="Filter by vendor (for purchases) or customer (for sales)"
    )
    
    # Add date range filters
    acquisition_date_from = fields.Date(string="Acquisition Date From")
    acquisition_date_to = fields.Date(string="Acquisition Date To")
    
    # Add value range filters
    min_value = fields.Float(string="Minimum Value", default=0.0)
    max_value = fields.Float(string="Maximum Value")
    # ============ END MAIN FIELDS ============

    @api.model
    def default_get(self, fields_list):
        defaults = super(FixedAssetRegisterWizard, self).default_get(fields_list)
        # Set default date_as_of to today
        defaults['date_as_of'] = fields.Date.context_today(self)
        return defaults
    
    # ============ NEW COMPUTED METHODS ============
    def _compute_has_data(self):
        for wizard in self:
            wizard.has_data = bool(wizard.asset_lines_json and wizard.asset_lines_json != '[]')

    @api.depends('asset_lines_json')
    def _compute_asset_lines_html(self):
        for wizard in self:
            html_content = ""
            try:
                lines = json.loads(wizard.asset_lines_json or '[]')
                if lines:
                    html_content = """
                    <div class="table-responsive">
                        <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <thead>
                                <tr style="background-color: #f2f2f2;">
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Asset Code</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Asset Name</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Category</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: center;">Acq. Date</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Original Value</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Accum. Dep</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Net Value</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Custodian</th>
                                    <th style="padding: 8px; border: 1px solid #ddd; text-align: center;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    
                    total_original = 0
                    total_dep = 0
                    total_net = 0
                    asset_count = 0
                    current_category = None
                    
                    for line in lines:
                        category = line.get('category', '')
                        
                        # Add category header if changed
                        if current_category != category:
                            if current_category is not None:
                                # Add category total
                                html_content += f"""
                                <tr style="background-color: #e8f4f8; font-weight: bold;">
                                    <td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">
                                        {current_category} Total:
                                    </td>
                                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_original:.2f}</td>
                                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_dep:.2f}</td>
                                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_net:.2f}</td>
                                    <td colspan="2"></td>
                                </tr>
                                """
                            
                            html_content += f"""
                            <tr style="background-color: #d9edf7; color: #31708f; font-weight: bold;">
                                <td colspan="9" style="padding: 8px; border: 1px solid #ddd;">
                                    Category: {category}
                                </td>
                            </tr>
                            """
                            current_category = category
                            cat_original = 0
                            cat_dep = 0
                            cat_net = 0
                        
                        original_val = float(line.get('original_value', 0))
                        dep_val = float(line.get('accumulated_dep', 0))
                        net_val = float(line.get('net_book_value', 0))
                        
                        total_original += original_val
                        total_dep += dep_val
                        total_net += net_val
                        cat_original += original_val
                        cat_dep += dep_val
                        cat_net += net_val
                        asset_count += 1
                        
                        status = line.get('status', '')
                        status_class = "text-success" if status == 'Active' else "text-warning"
                        
                        html_content += f"""
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;">{line.get('asset_code', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{line.get('asset_name', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{category}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{line.get('acquisition_date', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{original_val:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{dep_val:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{net_val:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{line.get('custodian', '')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;" class="{status_class}">{status}</td>
                        </tr>
                        """
                    
                    # Add final category total
                    if current_category is not None:
                        html_content += f"""
                        <tr style="background-color: #e8f4f8; font-weight: bold;">
                            <td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">
                                {current_category} Total:
                            </td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_original:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_dep:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{cat_net:.2f}</td>
                            <td colspan="2"></td>
                        </tr>
                        """
                    
                    # Add grand total
                    html_content += f"""
                        <tr style="background-color: #d4edda; border-top: 2px solid #155724; font-weight: bold;">
                            <td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">
                                GRAND TOTAL ({asset_count} Assets):
                            </td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_original:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_dep:.2f}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_net:.2f}</td>
                            <td colspan="2"></td>
                        </tr>
                    """
                    
                    html_content += """
                            </tbody>
                        </table>
                    </div>
                    """
            except Exception as e:
                html_content = f"<p style='color: red;'>Error displaying asset data: {str(e)}</p>"
            
            wizard.asset_lines_html = html_content

    @api.depends('asset_lines_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                lines = json.loads(wizard.asset_lines_json or '[]')
                wizard.total_assets = len(lines)
                wizard.total_original_value = sum(float(line.get('original_value', 0)) for line in lines)
                wizard.total_depreciation = sum(float(line.get('accumulated_dep', 0)) for line in lines)
                wizard.total_net_value = sum(float(line.get('net_book_value', 0)) for line in lines)
            except:
                wizard.total_assets = 0
                wizard.total_original_value = 0
                wizard.total_depreciation = 0
                wizard.total_net_value = 0
    # ============ END NEW COMPUTED METHODS ============

    # ============ NEW GENERATE ACTION ============
    def action_generate_assets(self):
        """
        Generate asset data and display in wizard
        """
        self.ensure_one()
        
        # Validate dates if applicable
        if self.acquisition_date_from and self.acquisition_date_to:
            if self.acquisition_date_from > self.acquisition_date_to:
                raise UserError(_("Acquisition Date From cannot be after Acquisition Date To."))
        
        # Get asset data
        lines_data = self._get_assets()
        
        # Convert dates to strings for JSON serialization
        serializable_data = self._prepare_serializable_data(lines_data)
        
        # Store as JSON
        self.asset_lines_json = json.dumps(serializable_data)
        
        # Return action to refresh the view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _prepare_serializable_data(self, lines_data):
        """
        Convert non-serializable objects (like dates) to strings for JSON storage
        """
        serializable_lines = []
        for line in lines_data:
            serializable_line = {}
            for key, value in line.items():
                if isinstance(value, (date, datetime)):
                    # Convert date/datetime to string
                    serializable_line[key] = value.strftime('%Y-%m-%d') if value else ''
                elif isinstance(value, float):
                    # Ensure floats are serializable
                    serializable_line[key] = float(value)
                elif isinstance(value, int):
                    serializable_line[key] = int(value)
                elif value is None:
                    serializable_line[key] = ''
                else:
                    serializable_line[key] = value
            serializable_lines.append(serializable_line)
        return serializable_lines
    # ============ END NEW GENERATE ACTION ============

    # ============ MODIFY PRINT ACTION ============
    def action_print_fixed_asset_register(self):
        """
        Called by the wizard's Print button.
        """
        self._check_access()
        
        # Validate that we have data to print
        if not self.asset_lines_json or self.asset_lines_json == '[]':
            raise UserError(_("Please generate asset data first using the 'Generate' button."))
        
        return self.env.ref('dw_customer_credit.action_report_fixed_asset_register').report_action(self)
    # ============ END MODIFY PRINT ACTION ============
    
    # ============ ADD METHOD FOR REPORT TEMPLATE ============
    def get_asset_lines(self):
        """Get parsed lines for report template"""
        self.ensure_one()
        try:
            return json.loads(self.asset_lines_json or '[]')
        except:
            return []
    # ============ END ADD METHOD ============

    def _get_assets(self):
        """
        Method to get fixed assets data from the actual asset module.
        """
        # Build search domain
        domain = []
        
        # Add status filter
        if self.state and self.state != 'all':
            domain.append(('state', '=', self.state))
        
        # Add category filter if selected
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        
        # Add partner filter if selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        # Add acquisition date range filters
        if self.acquisition_date_from:
            domain.append(('date', '>=', self.acquisition_date_from))
        if self.acquisition_date_to:
            domain.append(('date', '<=', self.acquisition_date_to))
        
        # Add value range filters (but don't exclude assets with 0 value)
        if self.min_value and self.min_value > 0:
            domain.append(('value', '>=', self.min_value))
        if self.max_value and self.max_value > 0:
            domain.append(('value', '<=', self.max_value))
        
        # REMOVE sort logic - use default ordering
        order_by = 'category_id, date, name'
        
        # Search for assets
        assets = self.env['account.asset.asset'].search(domain, order=order_by)
        
        lines = []
        
        for asset in assets:
            # Add a check for missing date but don't skip
            if not asset.date:
                # Use a default date if none exists
                asset_date = fields.Date.today()
            else:
                asset_date = asset.date
                
            # Calculate values as of the selected date
            values = self._calculate_asset_values_as_of_date(asset, self.date_as_of)
            
            # Determine asset category for filtering
            asset_category = asset.category_id.name if asset.category_id else 'Uncategorized'
            asset_type = asset.type if asset.type else 'purchase'
            
            # Get custodian/owner (partner)
            custodian = asset.partner_id.name if asset.partner_id else ''
            
            # Determine status with proper labels
            status_dict = {
                'draft': 'Draft',
                'open': 'Active',
            }
            status = status_dict.get(asset.state, asset.state.capitalize())
            
            # Calculate useful life in years
            useful_life_years = self._calculate_useful_life(asset)
            
            # Get acquisition date - ensure it's a date object
            acquisition_date = asset_date
            
            # Calculate asset age
            asset_age = self._calculate_asset_age(acquisition_date, self.date_as_of)
            
            lines.append({
                'asset_code': asset.code or f"AST-{asset.id:04d}",
                'asset_name': asset.name,
                'category': asset_category,
                'acquisition_date': acquisition_date,  # This is a date object
                'original_value': asset.value or 0.0,
                'accumulated_dep': values['accumulated_depreciation'],
                'net_book_value': values['net_book_value'],
                'location': '',  # This module doesn't have location field
                'custodian': custodian,
                'depreciation_method': asset.method.capitalize() if asset.method else 'Linear',
                'useful_life': useful_life_years,
                'salvage_value': asset.salvage_value or 0.0,
                'status': status,
                'asset_type': asset_type.capitalize(),
                'asset_id': asset.id,
                'asset_age': asset_age,
                'depreciation_rate': self._calculate_depreciation_rate(asset, values['accumulated_depreciation']),
                'note': asset.note or '',
            })
        
        # If no assets found, return sample data for demonstration
        if not lines:
            lines = self._get_sample_assets()
            
        return lines
    
    def _get_sample_assets(self):
        """
        Fallback method to return sample asset data if no real assets found.
        Only used for demonstration purposes.
        """
        today = fields.Date.today()
        return [
            {
                'asset_code': 'NO-ASSETS-FOUND',
                'asset_name': 'No Assets Found Matching Criteria',
                'category': 'Information',
                'acquisition_date': today,  # This is a date object
                'original_value': 0.00,
                'accumulated_dep': 0.00,
                'net_book_value': 0.00,
                'location': 'System',
                'custodian': 'Administrator',
                'depreciation_method': 'N/A',
                'useful_life': 0,
                'salvage_value': 0.00,
                'status': 'No Data',
                'asset_type': 'Information',
                'asset_age': 0,
                'depreciation_rate': 0.0,
                'note': 'Please check if assets have values > 0, or try different filters',
            },
        ]
    
    # Keep all other methods as they were (_is_asset_valid_for_report, _calculate_asset_values_as_of_date, etc.)
    def _is_asset_valid_for_report(self, asset):
        """Check if asset has valid data for reporting"""
        return True
    
    def _calculate_asset_values_as_of_date(self, asset, date_as_of):
        """
        Calculate asset values as of a specific date.
        This calculates accumulated depreciation up to the selected date.
        """
        try:
            # Get original value
            original_value = asset.value or 0.0
            salvage_value = asset.salvage_value or 0.0
            
            # Initialize accumulated depreciation
            accumulated_depreciation = 0.0
            
            # Calculate depreciation from depreciation lines
            if asset.depreciation_line_ids:
                # Filter depreciation lines up to the selected date and that are posted
                dep_lines = asset.depreciation_line_ids.filtered(
                    lambda l: l.depreciation_date <= date_as_of and l.move_check
                )
                
                # Sum depreciation amounts
                accumulated_depreciation = sum(dep_lines.mapped('amount'))
            
            # Calculate net book value
            depreciable_value = original_value - salvage_value
            net_book_value = max(0.0, depreciable_value - accumulated_depreciation)
            
            # Adjust accumulated depreciation to not exceed depreciable value
            if accumulated_depreciation > depreciable_value:
                accumulated_depreciation = depreciable_value
            
            return {
                'original_value': original_value,
                'accumulated_depreciation': accumulated_depreciation,
                'net_book_value': net_book_value + salvage_value,
                'depreciable_value': depreciable_value,
                'remaining_depreciable_value': max(0.0, depreciable_value - accumulated_depreciation),
            }
            
        except Exception as e:
            # Fallback to asset's residual value calculation
            return {
                'original_value': asset.value or 0.0,
                'accumulated_depreciation': (asset.value or 0.0) - (asset.value_residual or 0.0),
                'net_book_value': asset.value_residual or 0.0,
            }
    
    def _calculate_useful_life(self, asset):
        """Calculate useful life in years"""
        if asset.method_time == 'number' and asset.method_number and asset.method_period:
            # Convert months to years
            total_months = asset.method_number * asset.method_period
            return total_months / 12.0
        return 0.0
    
    def _calculate_asset_age(self, acquisition_date, as_of_date):
        """Calculate asset age in years"""
        if not acquisition_date or not as_of_date:
            return 0
        
        # Convert to date objects if they are strings
        if isinstance(acquisition_date, str):
            try:
                acquisition_date = datetime.strptime(acquisition_date, '%Y-%m-%d').date()
            except:
                acquisition_date = fields.Date.today()
        if isinstance(as_of_date, str):
            try:
                as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
            except:
                as_of_date = fields.Date.today()
        
        # Calculate difference in years
        delta = relativedelta(as_of_date, acquisition_date)
        return delta.years + delta.months / 12.0 + delta.days / 365.0
    
    def _calculate_depreciation_rate(self, asset, accumulated_dep):
        """Calculate depreciation rate percentage"""
        if not asset.value or asset.value <= 0:
            return 0.0
        
        depreciable_value = asset.value - (asset.salvage_value or 0)
        if depreciable_value <= 0:
            return 0.0
        
        return (accumulated_dep / depreciable_value) * 100