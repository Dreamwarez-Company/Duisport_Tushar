from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import date
import json

class InventoryCostingWizard(models.TransientModel):
    _name = "inventory.costing.wizard"
    _description = "Inventory & Costing Report Wizard"

    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.context_today)
    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Category")
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Transaction Report'),
    ], string="Report Type", default='summary', required=True)
    
    # JSON data storage for preview
    report_data_json = fields.Text(string="Report Data", default="{}")
    has_data = fields.Boolean(string="Has Data", compute='_compute_has_data', store=False)
    
    # Computed fields for display
    total_value = fields.Float(string="Total Value", compute='_compute_totals', store=False)
    total_items = fields.Integer(string="Total Items", compute='_compute_totals', store=False)
    
    # HTML preview
    report_data_html = fields.Html(string="Report Preview", compute='_compute_report_data_html', store=False)
    
    @api.depends('report_data_json')
    def _compute_has_data(self):
        for wizard in self:
            try:
                data = json.loads(wizard.report_data_json or '{}')
                wizard.has_data = bool(data.get('summary_data') or data.get('transactions'))
            except:
                wizard.has_data = False
    
    @api.depends('report_data_json')
    def _compute_totals(self):
        for wizard in self:
            try:
                data = json.loads(wizard.report_data_json or '{}')
                if wizard.report_type == 'summary':
                    wizard.total_value = data.get('total_value', 0)
                    wizard.total_items = len(data.get('summary_data', []))
                else:
                    wizard.total_value = data.get('total_cost', 0)
                    wizard.total_items = len(data.get('transactions', []))
            except:
                wizard.total_value = 0
                wizard.total_items = 0
    
    @api.depends('report_data_json', 'report_type')
    def _compute_report_data_html(self):
        for wizard in self:
            html_content = ""
            try:
                data = json.loads(wizard.report_data_json or '{}')
                
                if wizard.report_type == 'summary':
                    summary_data = data.get('summary_data', [])
                    if summary_data:
                        html_content = self._generate_summary_html(summary_data, data.get('total_value', 0))
                
                elif wizard.report_type == 'detailed':
                    transactions = data.get('transactions', [])
                    if transactions:
                        html_content = self._generate_detailed_html(transactions, data.get('total_cost', 0))
                
                if not html_content:
                    html_content = "<p>No data to display. Click 'Generate' to create report.</p>"
                    
            except Exception as e:
                html_content = f"<p>Error displaying data: {str(e)}</p>"
            
            wizard.report_data_html = html_content
    
    def _generate_summary_html(self, summary_data, total_value):
        """Generate HTML for summary report preview - WITHOUT Product Code column"""
        html = """
        <div class="table-responsive">
            <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Product Name</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Category</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Quantity</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Unit Cost</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total Value</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for item in summary_data:
            html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{item.get('product_name', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{item.get('category', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{item.get('quantity', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{item.get('unit_cost', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{item.get('total_value', 0):.2f}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr style="border-top: 2px solid #000; font-weight: bold;">
                        <td colspan="4" style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total:</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_value:.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """
        
        return html
    
    def _generate_detailed_html(self, transactions, total_cost):
        """Generate HTML for detailed report preview - WITHOUT Product Code column"""
        html = """
        <div class="table-responsive">
            <table class="table table-striped table-bordered" style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Date</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Product</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Reference</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Quantity</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Unit Cost</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total Cost</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for txn in transactions:
            html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{txn.get('date', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{txn.get('product_name', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{txn.get('reference', '')}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{txn.get('quantity', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{txn.get('unit_cost', 0):.2f}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{txn.get('total_cost', 0):.2f}</td>
                </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr style="border-top: 2px solid #000; font-weight: bold;">
                        <td colspan="5" style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total:</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_cost:.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """
        
        return html
    
    def action_generate_inventory_data(self):
        """Generate inventory data and display preview"""
        self.ensure_one()
        
        # Validate dates
        if self.start_date > self.end_date:
            raise UserError("Start date cannot be after end date.")
        
        print("=" * 80)
        print("INVENTORY WIZARD: Generating report data...")
        
        # Get report data
        data = self._get_report_data()
        
        # Store as JSON
        self.report_data_json = json.dumps(data)
        
        print(f"Data stored in JSON, has_data: {self.has_data}")
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
    
    # def action_print_inventory_costing(self):
    #     """
    #     Called by the wizard's Print button.
    #     """
    #     self.ensure_one()
        
    #     # Validate that we have data to print
    #     if not self.has_data:
    #         raise UserError("Please generate inventory data first using the 'Generate' button.")
        
    #     print("=" * 80)
    #     print("INVENTORY WIZARD: Printing report...")
    #     print(f"Wizard ID: {self.id}")
    #     print(f"Has data: {self.has_data}")
        
    #     # Use the correct report reference
    #     return self.env.ref('dw_customer_credit.report_inventory_costing_template').report_action(self)


    def action_print_inventory_costing(self):
        """
        Called by the wizard's Print button.
        """
        self.ensure_one()
        
        # Validate that we have data to print
        if not self.has_data:
            raise UserError("Please generate inventory data first using the 'Generate' button.")
        
        print("=" * 80)
        print("INVENTORY WIZARD: Printing report...")
        print(f"Wizard ID: {self.id}")
        print(f"Has data: {self.has_data}")
        
        # Use the REPORT ACTION, not the template
        return self.env.ref('dw_customer_credit.action_report_inventory_costing').report_action(self)
    
    def _get_report_data(self):
        """
        Get inventory data - Enhanced version with better calculations
        """
        print("=" * 80)
        print("INVENTORY WIZARD: Getting report data...")
        print(f"Report type: {self.report_type}")
        
        data_result = {}
        
        if self.report_type == 'summary':
            print("Generating summary report")
            
            # Get all products with stock
            product_domain = [
                ('type', '=', 'product'),
                ('qty_available', '!=', 0)  # Only products with stock
            ]
            
            if self.product_id:
                product_domain.append(('id', '=', self.product_id.id))
            if self.product_category_id:
                product_domain.append(('categ_id', '=', self.product_category_id.id))
            
            products = self.env['product.product'].search(product_domain)
            print(f"Found {len(products)} products with stock")
            
            summary_data = []
            total_value = 0
            
            for product in products:
                # Get actual quantities using stock quant
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('quantity', '>', 0)
                ])
                
                quantity = sum(quant.quantity for quant in quants)
                
                if quantity > 0:
                    # Get standard price or average cost
                    standard_price = product.standard_price or product.product_tmpl_id.standard_price or 0
                    total_product_value = quantity * standard_price
                    total_value += total_product_value
                    
                    summary_data.append({
                        'product_code': product.default_code or product.barcode or '',
                        'product_name': product.name,
                        'category': product.categ_id.complete_name if product.categ_id else '',
                        'uom': product.uom_id.name if product.uom_id else '',
                        'quantity': quantity,
                        'unit_cost': standard_price,
                        'total_value': total_product_value,
                    })
                    
                    print(f"Product: {product.name}, Qty: {quantity}, Price: {standard_price}, Value: {total_product_value}")
            
            data_result['summary_data'] = summary_data
            data_result['total_value'] = total_value
            
        elif self.report_type == 'detailed':
            print("Generating detailed report")
            
            # Get stock moves with enhanced domain
            move_domain = [
                ('state', '=', 'done'),
                ('product_id.type', '=', 'product'),
                ('quantity', '>', 0)
            ]
            
            # Add date filter
            if self.start_date:
                move_domain.append(('date', '>=', self.start_date))
            if self.end_date:
                move_domain.append(('date', '<=', self.end_date))
            
            if self.product_id:
                move_domain.append(('product_id', '=', self.product_id.id))
            if self.product_category_id:
                move_domain.append(('product_id.categ_id', 'child_of', self.product_category_id.id))
            
            moves = self.env['stock.move'].search(move_domain, order='date asc')
            print(f"Found {len(moves)} stock moves")
            
            transactions = []
            total_cost = 0
            
            for move in moves:
                product = move.product_id
                
                # Determine move type for description
                if move.picking_type_id:
                    if move.picking_type_id.code == 'incoming':
                        move_type = "Receipt"
                    elif move.picking_type_id.code == 'outgoing':
                        move_type = "Delivery"
                    else:
                        move_type = "Internal"
                else:
                    move_type = "Transfer"
                
                # Get quantity and unit cost
                quantity = move.quantity_done if hasattr(move, 'quantity_done') else move.product_uom_qty
                
                # Try to get actual cost from valuation layers
                unit_cost = product.standard_price or 0
                valuation_layers = self.env['stock.valuation.layer'].search([
                    ('stock_move_id', '=', move.id)
                ], limit=1)
                
                if valuation_layers:
                    unit_cost = valuation_layers.unit_cost or unit_cost
                
                total_move_cost = quantity * unit_cost
                total_cost += total_move_cost
                
                transactions.append({
                    'date': move.date.strftime('%Y-%m-%d') if move.date else '',
                    'product_code': product.default_code or product.barcode or '',
                    'product_name': product.name,
                    'reference': move.picking_id.name or move.origin or move.reference or move.name or '',
                    'move_type': move_type,
                    'quantity': quantity,
                    'unit_cost': unit_cost,
                    'total_cost': total_move_cost,
                })
                
                print(f"Added transaction: {product.name}, Type: {move_type}, Qty: {quantity}, Cost: {unit_cost}")
            
            data_result['transactions'] = transactions
            data_result['total_cost'] = total_cost
        
        print(f"Returning data with {len(data_result.get('summary_data', data_result.get('transactions', [])))} items")
        print("=" * 80)
        
        return data_result
    
    def get_report_data(self):
        """Get parsed report data for templates"""
        self.ensure_one()
        try:
            return json.loads(self.report_data_json or '{}')
        except:
            return {}