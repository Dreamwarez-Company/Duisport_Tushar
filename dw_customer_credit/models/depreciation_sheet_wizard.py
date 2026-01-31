from odoo import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessError

class DepreciationSheetWizard(models.TransientModel):
    _name = "depreciation.sheet.wizard"
    _description = "Depreciation Sheet Wizard"
    _inherit = ['mail.thread']

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
                raise AccessError(_("You don't have permission to create depreciation reports."))
            return False
        return super().check_access_rights(operation, raise_exception)

    # Add automatic access control
    @api.model
    def _check_access(self):
        """Basic access control for the wizard"""
        if not self.env.user.has_group('base.group_user'):
            raise AccessError(_("You need to be logged in to access this feature."))
        return True
    
    def action_print_depreciation_sheet(self):
        """
        Called by the wizard's Print button.
        """
        self._check_access()
        return self.env.ref('dw_customer_credit.action_report_depreciation_sheet').report_action(self)
    
    date_from = fields.Date(string="From Date", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To Date", required=True, default=fields.Date.context_today)
    
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
    
    # Add status filter
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('all', 'All Status'),
    ], string="Status", default='open')
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(DepreciationSheetWizard, self).default_get(fields_list)
        # Set default dates to current month
        today = fields.Date.context_today(self)
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1, days=-1))
        defaults['date_from'] = first_day
        defaults['date_to'] = last_day
        return defaults

    def _get_depreciation_data(self):
        """
        Method to get depreciation data for the selected period.
        """
        # Build search domain for assets
        domain = []
        
        # Add status filter
        if self.state and self.state != 'all':
            domain.append(('state', '=', self.state))
        else:
            # Default to show running assets
            domain.append(('state', '=', 'open'))
        
        # Add category filter if selected
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        
        # Add partner filter if selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        # Search for assets
        assets = self.env['account.asset.asset'].search(domain, order='category_id, date, name')
        
        lines = []
        total_period_depreciation = 0.0
        total_assets = 0
        
        for asset in assets:
            # Get all depreciation lines for this asset
            if not asset.depreciation_line_ids:
                continue
                
            # Filter depreciation lines within the period
            period_dep_lines = asset.depreciation_line_ids.filtered(
                lambda l: l.depreciation_date and 
                         l.depreciation_date >= self.date_from and 
                         l.depreciation_date <= self.date_to
            )
            
            if not period_dep_lines:
                continue
                
            # Calculate total depreciation for the period
            period_depreciation = sum(period_dep_lines.mapped('amount'))
            
            if period_depreciation <= 0:
                continue
                
            # Determine asset category
            asset_category = asset.category_id.name if asset.category_id else 'Uncategorized'
            
            # Get custodian/owner (partner)
            custodian = asset.partner_id.name if asset.partner_id else ''
            
            # Calculate useful life in years
            useful_life_years = self._calculate_useful_life(asset)
            
            # Get acquisition date
            acquisition_date = asset.date
            if isinstance(acquisition_date, str):
                try:
                    acquisition_date = datetime.strptime(str(acquisition_date), '%Y-%m-%d').date()
                except:
                    acquisition_date = fields.Date.today()
            
            # Calculate accumulated depreciation up to date_from (before period)
            accumulated_before = self._calculate_accumulated_depreciation_before(asset, self.date_from)
            
            # Calculate accumulated depreciation up to date_to (after period)
            accumulated_after = accumulated_before + period_depreciation
            
            # Calculate net book value at start and end
            original_value = asset.value or 0.0
            salvage_value = asset.salvage_value or 0.0
            nbv_start = max(0.0, original_value - salvage_value - accumulated_before) + salvage_value
            nbv_end = max(0.0, original_value - salvage_value - accumulated_after) + salvage_value
            
            # Get depreciation method details
            depreciation_method = asset.method.capitalize() if asset.method else 'Linear'
            
            # Calculate depreciation rate (annual)
            depreciation_rate = self._calculate_annual_depreciation_rate(asset)
            
            # Get depreciation line details for the period
            depreciation_line_details = []
            for dep_line in period_dep_lines.sorted(key=lambda l: l.depreciation_date):
                depreciation_line_details.append({
                    'date': dep_line.depreciation_date,
                    'amount': dep_line.amount,
                    'move_id': dep_line.move_id.name if dep_line.move_id else '',
                    'move_check': dep_line.move_check,
                    'move_posted_check': dep_line.move_posted_check,
                    'sequence': dep_line.sequence,
                    'name': dep_line.name,
                })
            
            lines.append({
                'asset_code': asset.code or f"AST-{asset.id:04d}",
                'asset_name': asset.name,
                'category': asset_category,
                'acquisition_date': acquisition_date,
                'original_value': original_value,
                'salvage_value': salvage_value,
                'depreciation_rate': depreciation_rate,
                'depreciation_method': depreciation_method,
                'useful_life': useful_life_years,
                'accumulated_before': accumulated_before,
                'period_depreciation': period_depreciation,
                'accumulated_after': accumulated_after,
                'nbv_start': nbv_start,
                'nbv_end': nbv_end,
                'custodian': custodian,
                'asset_id': asset.id,
                'depreciation_lines': depreciation_line_details,
                'method_number': asset.method_number,
                'method_period': asset.method_period,
                'asset_state': asset.state,
            })
            
            total_period_depreciation += period_depreciation
            total_assets += 1
        
        # If no depreciation data found
        if not lines:
            lines = self._get_sample_depreciation_data()
            total_assets = 1
            total_period_depreciation = 0
        
        return {
            'lines': lines,
            'total_period_depreciation': total_period_depreciation,
            'total_assets': total_assets,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
    
    def _calculate_accumulated_depreciation_before(self, asset, date_from):
        """
        Calculate accumulated depreciation up to (but not including) a specific date.
        """
        accumulated = 0.0
        
        if asset.depreciation_line_ids:
            # Filter depreciation lines before the date
            dep_lines = asset.depreciation_line_ids.filtered(
                lambda l: l.depreciation_date and l.depreciation_date < date_from
            )
            
            # Sum depreciation amounts
            accumulated = sum(dep_lines.mapped('amount'))
        
        return accumulated
    
    def _calculate_useful_life(self, asset):
        """Calculate useful life in years"""
        if asset.method_time == 'number' and asset.method_number and asset.method_period:
            # Convert months to years
            total_months = asset.method_number * asset.method_period
            return total_months / 12.0
        return 0.0
    
    def _calculate_annual_depreciation_rate(self, asset):
        """Calculate annual depreciation rate percentage"""
        if not asset.value or asset.value <= 0:
            return 0.0
        
        salvage_value = asset.salvage_value or 0
        depreciable_value = asset.value - salvage_value
        
        if depreciable_value <= 0:
            return 0.0
        
        # Calculate annual depreciation amount
        if asset.method == 'linear' and asset.method_number and asset.method_period:
            total_months = asset.method_number * asset.method_period
            if total_months > 0:
                monthly_depreciation = depreciable_value / total_months
                annual_depreciation = monthly_depreciation * 12
                return (annual_depreciation / depreciable_value) * 100
        
        return 0.0
    
    def _get_sample_depreciation_data(self):
        """
        Fallback method to return sample depreciation data.
        """
        today = fields.Date.today()
        return [{
            'asset_code': 'NO-DEPRECIATION-FOUND',
            'asset_name': 'No Depreciation Data Found for Selected Period',
            'category': 'Information',
            'acquisition_date': today,
            'original_value': 0.00,
            'salvage_value': 0.00,
            'depreciation_rate': 0,
            'depreciation_method': 'N/A',
            'useful_life': 0,
            'accumulated_before': 0.00,
            'period_depreciation': 0.00,
            'accumulated_after': 0.00,
            'nbv_start': 0.00,
            'nbv_end': 0.00,
            'custodian': 'Administrator',
            'asset_id': 0,
            'depreciation_lines': [],
            'method_number': 0,
            'method_period': 0,
            'asset_state': 'draft',
        }]