from odoo import models, fields, api
from odoo.exceptions import UserError
import json
from datetime import date, datetime, timedelta

class WipValuationWizard(models.TransientModel):
    _name = "wip.valuation.wizard"
    _description = "WIP Valuation Report Wizard"

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.context_today)
    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Category")
    
    # JSON data storage for preview
    report_data_json = fields.Text(string="Report Data", default="{}")
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Computed fields for display
    total_wip_value = fields.Float(string="Total WIP Value", compute='_compute_totals', store=False)
    total_items = fields.Integer(string="Total Items", compute='_compute_totals', store=False)
    
    # HTML preview
    report_data_html = fields.Html(string="Report Preview", compute='_compute_report_data_html', store=False)
    
    @api.depends('report_data_json')
    def _compute_has_data(self):
        for wizard in self:
            try:
                data = json.loads(wizard.report_data_json or '{}')
                wizard.has_data = bool(data.get('lines'))
            except:
                wizard.has_data = False
    
    @api.depends('report_data_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                data = json.loads(wizard.report_data_json or '{}')
                wizard.total_wip_value = data.get('total_wip_value', 0)
                wizard.total_items = len(data.get('lines', []))
            except:
                wizard.total_wip_value = 0
                wizard.total_items = 0
    
    @api.depends('report_data_json')
    def _compute_report_data_html(self):
        for wizard in self:
            html_content = ""
            try:
                data = json.loads(wizard.report_data_json or '{}')
                lines = data.get('lines', [])
                
                if lines:
                    html_content = self._generate_wip_html(lines, data.get('total_wip_value', 0))
                else:
                    html_content = "<p>No data to display. Click 'Generate' to create report.</p>"
                    
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.report_data_html = html_content
    
    def _generate_wip_html(self, lines, total_wip_value):
        """Generate HTML for WIP report preview"""
        html = """
        <div class="table-responsive">
            <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Date</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Product</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Quantity</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Value</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Location</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for line in lines:
            html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{line.get('date', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{line.get('product', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{line.get('qty', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{line.get('value', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{line.get('location', '')}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr style="border-top: 2px solid #000; font-weight: bold;">
                        <td colspan="3" style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total WIP Value:</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_wip_value:.2f}</td>
                        <td style="padding: 8px; border: 1px solid #ddd;"></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """
        
        return html
    
    def action_generate_wip_data(self):
        """Generate WIP data and display preview"""
        self.ensure_one()
        
        # Validate dates
        if self.start_date > self.end_date:
            raise UserError("Start date cannot be after end date.")
        
        print("=" * 80)
        print("WIP VALUATION WIZARD: Generating report data...")
        print(f"Start Date: {self.start_date}")
        print(f"End Date: {self.end_date}")
        
        # Get report data
        data = self._get_wip_report_data()
        
        # Store as JSON
        self.report_data_json = json.dumps(data)
        
        print(f"Data stored in JSON, has_data: {self.has_data}")
        print(f"Total lines: {len(data.get('lines', []))}")
        print(f"Total WIP Value: {data.get('total_wip_value', 0)}")
        print("=" * 80)
        
        # Return action to refresh view
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
    
    def action_print_wip_report(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have data to print
        if not self.has_data:
            raise UserError("Please generate WIP data first using the 'Generate' button.")
        
        print("=" * 80)
        print("WIP VALUATION WIZARD: Printing report...")
        print(f"Wizard ID: {self.id}")
        print(f"Has data: {self.has_data}")
        
        # Use the REPORT ACTION ID
        try:
            report_action = self.env.ref('dw_customer_credit.action_report_wip_valuation')
            return report_action.report_action(self)
        except Exception as e:
            print(f"Error getting report action: {str(e)}")
            # Fallback: use direct report generation
            return {
                'type': 'ir.actions.report',
                'report_name': 'dw_customer_credit.report_wip_valuation_template',
                'model': 'wip.valuation.wizard',
                'report_type': 'qweb-pdf',
                'data': {'docids': self.ids},
                'context': self.env.context,
            }
    
    def _get_wip_report_data(self):
        """
        Get WIP valuation data - FIXED for Odoo 17
        """
        print("=" * 80)
        print("WIP VALUATION: Getting report data...")
        
        # Try multiple approaches to get WIP data
        lines = []
        total_wip_value = 0
        
        # Approach 1: Try manufacturing orders with correct field names
        lines, total_wip_value = self._get_wip_from_mo()
        
        # Approach 2: If no MO data, try stock moves
        if not lines:
            print("No manufacturing orders found, trying stock moves approach...")
            lines, total_wip_value = self._get_wip_from_stock_moves()
        
        # Approach 3: If still no data, try work orders
        if not lines:
            print("No stock moves found, trying work orders...")
            lines, total_wip_value = self._get_wip_from_work_orders()
        
        return {
            'lines': lines,
            'total_wip_value': total_wip_value,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else '',
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else '',
        }
    
    def _get_wip_from_mo(self):
        """Get WIP data from manufacturing orders - FIXED for Odoo 17"""
        print("Getting WIP from manufacturing orders...")
        
        # Build domain for manufacturing orders - using correct field names
        mo_domain = [
            ('state', 'in', ['confirmed', 'progress', 'to_close', 'done']),
        ]
        
        # Try different date fields that might exist in Odoo 17
        # Common fields: date_planned_start, date_planned_finished, create_date, write_date
        date_field = None
        
        # Check which date fields exist in mrp.production
        mo_model = self.env['mrp.production']
        available_fields = mo_model.fields_get()
        
        # Try to find a date field
        possible_date_fields = ['date_planned_start', 'date_planned_finished', 'date_start', 
                               'date_finished', 'create_date', 'write_date']
        
        for field in possible_date_fields:
            if field in available_fields:
                date_field = field
                break
        
        if date_field:
            mo_domain.append((date_field, '>=', self.start_date))
            mo_domain.append((date_field, '<=', self.end_date))
            print(f"Using date field: {date_field}")
        else:
            print("No suitable date field found in mrp.production")
        
        if self.product_id:
            mo_domain.append(('product_id', '=', self.product_id.id))
        if self.product_category_id:
            mo_domain.append(('product_id.categ_id', 'child_of', self.product_category_id.id))
        
        print(f"MO search domain: {mo_domain}")
        
        try:
            manufacturing_orders = self.env['mrp.production'].search(mo_domain)
            print(f"Found {len(manufacturing_orders)} manufacturing orders")
        except Exception as e:
            print(f"Error searching manufacturing orders: {str(e)}")
            manufacturing_orders = self.env['mrp.production']
        
        lines = []
        total_wip_value = 0
        
        for mo in manufacturing_orders:
            # Calculate WIP value
            wip_value = self._calculate_mo_wip_value(mo)
            
            if wip_value > 0:
                # Get product information
                product = mo.product_id
                product_name = product.display_name if product else ''
                
                # Get location
                location = ''
                if hasattr(mo, 'location_src_id') and mo.location_src_id:
                    location = mo.location_src_id.complete_name
                elif hasattr(mo, 'location_id') and mo.location_id:
                    location = mo.location_id.complete_name
                
                # Get quantity
                quantity = 0
                if hasattr(mo, 'qty_producing') and mo.qty_producing:
                    quantity = mo.qty_producing
                elif hasattr(mo, 'product_qty') and mo.product_qty:
                    quantity = mo.product_qty
                
                # Get date
                mo_date = ''
                if date_field and hasattr(mo, date_field) and getattr(mo, date_field):
                    date_value = getattr(mo, date_field)
                    if isinstance(date_value, datetime):
                        mo_date = date_value.strftime('%Y-%m-%d')
                    elif isinstance(date_value, date):
                        mo_date = date_value.strftime('%Y-%m-%d')
                
                lines.append({
                    'date': mo_date,
                    'product': product_name,
                    'qty': quantity,
                    'value': wip_value,
                    'location': location,
                    'mo_reference': mo.name,
                    'state': mo.state,
                })
                
                total_wip_value += wip_value
                
                print(f"Added MO: {mo.name}, Product: {product_name}, "
                      f"Qty: {quantity}, Value: {wip_value}, State: {mo.state}")
        
        return lines, total_wip_value
    
    def _calculate_mo_wip_value(self, mo):
        """Calculate WIP value for a manufacturing order"""
        try:
            wip_value = 0
            
            # Method 1: Sum of raw material costs from done moves
            if hasattr(mo, 'move_raw_ids'):
                raw_material_cost = 0
                for move in mo.move_raw_ids.filtered(lambda m: m.state == 'done'):
                    # Get cost from valuation layers
                    valuation_layers = self.env['stock.valuation.layer'].search([
                        ('stock_move_id', '=', move.id)
                    ])
                    for layer in valuation_layers:
                        raw_material_cost += layer.value
                
                wip_value = raw_material_cost
            
            # Method 2: Use standard cost as fallback
            if wip_value == 0 and mo.product_id and mo.product_id.standard_price:
                quantity = 0
                if hasattr(mo, 'qty_producing') and mo.qty_producing:
                    quantity = mo.qty_producing
                elif hasattr(mo, 'product_qty') and mo.product_qty:
                    quantity = mo.product_qty
                
                wip_value = quantity * mo.product_id.standard_price
            
            return wip_value
            
        except Exception as e:
            print(f"Error calculating WIP value for MO {mo.name}: {str(e)}")
            return 0
    
    def _get_wip_from_stock_moves(self):
        """Alternative method to get WIP from stock moves"""
        print("Getting WIP from stock moves...")
        
        # Get stock moves for WIP locations
        move_domain = [
            ('state', '=', 'done'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ]
        
        # Try to filter by production locations if the field exists
        try:
            # Check if location_id.usage field exists in search
            test_move = self.env['stock.move'].search([], limit=1)
            if hasattr(test_move, 'location_id') and hasattr(test_move.location_id, 'usage'):
                move_domain.append(('location_id.usage', '=', 'production'))
                move_domain.append(('location_dest_id.usage', '=', 'internal'))
                print("Using location usage filters")
        except:
            print("Not using location usage filters")
        
        if self.product_id:
            move_domain.append(('product_id', '=', self.product_id.id))
        if self.product_category_id:
            move_domain.append(('product_id.categ_id', 'child_of', self.product_category_id.id))
        
        print(f"Stock moves search domain: {move_domain}")
        
        moves = self.env['stock.move'].search(move_domain)
        print(f"Found {len(moves)} stock moves")
        
        lines = []
        total_wip_value = 0
        
        for move in moves:
            product = move.product_id
            if not product:
                continue
            
            # Calculate value from valuation layers
            value = 0
            try:
                valuation_layers = self.env['stock.valuation.layer'].search([
                    ('stock_move_id', '=', move.id)
                ])
                
                for layer in valuation_layers:
                    value += layer.value
            except:
                # If valuation layers not available, use standard price
                value = move.product_uom_qty * (product.standard_price or 0)
            
            if value > 0:
                quantity = move.product_uom_qty
                
                # Get location names
                location_from = move.location_id.complete_name if hasattr(move.location_id, 'complete_name') else str(move.location_id)
                location_to = move.location_dest_id.complete_name if hasattr(move.location_dest_id, 'complete_name') else str(move.location_dest_id)
                location = f"{location_from} → {location_to}"
                
                lines.append({
                    'date': move.date.strftime('%Y-%m-%d') if move.date else '',
                    'product': product.display_name,
                    'qty': quantity,
                    'value': value,
                    'location': location,
                    'reference': move.picking_id.name or move.origin or move.name or '',
                    'move_type': 'Stock Move',
                })
                
                total_wip_value += value
                
                print(f"Added Move: {move.id}, Product: {product.display_name}, "
                      f"Qty: {quantity}, Value: {value}")
        
        return lines, total_wip_value
    
    def _get_wip_from_work_orders(self):
        """Get WIP data from work orders"""
        print("Getting WIP from work orders...")
        
        lines = []
        total_wip_value = 0
        
        try:
            # Check if workorder model exists
            if 'mrp.workorder' in self.env:
                wo_domain = [
                    ('state', 'in', ['ready', 'progress', 'done']),
                ]
                
                # Try to find a date field
                wo_model = self.env['mrp.workorder']
                available_fields = wo_model.fields_get()
                
                possible_date_fields = ['date_planned_start', 'date_planned_finished', 
                                       'date_start', 'date_finished', 'create_date']
                
                date_field = None
                for field in possible_date_fields:
                    if field in available_fields:
                        date_field = field
                        break
                
                if date_field:
                    wo_domain.append((date_field, '>=', self.start_date))
                    wo_domain.append((date_field, '<=', self.end_date))
                
                work_orders = self.env['mrp.workorder'].search(wo_domain)
                print(f"Found {len(work_orders)} work orders")
                
                for wo in work_orders:
                    # Calculate work order value (simplified)
                    # This could be based on labor hours, machine hours, etc.
                    if hasattr(wo, 'duration') and wo.duration:
                        # Example: $50 per hour of work
                        wo_value = wo.duration / 60 * 50  # Convert minutes to hours
                        
                        mo = wo.production_id
                        product_name = mo.product_id.display_name if mo and mo.product_id else ''
                        
                        lines.append({
                            'date': wo.date_start.strftime('%Y-%m-%d') if hasattr(wo, 'date_start') and wo.date_start else '',
                            'product': f"Work Order: {product_name}",
                            'qty': 1,
                            'value': wo_value,
                            'location': wo.workcenter_id.name if hasattr(wo, 'workcenter_id') and wo.workcenter_id else '',
                            'reference': wo.name,
                            'move_type': 'Work Order',
                        })
                        
                        total_wip_value += wo_value
                        
                        print(f"Added Work Order: {wo.name}, Value: {wo_value}")
        except Exception as e:
            print(f"Error getting work orders: {str(e)}")
        
        return lines, total_wip_value
    
    def get_report_data(self):
        """Get parsed report data for templates"""
        self.ensure_one()
        try:
            return json.loads(self.report_data_json or '{}')
        except:
            return {}