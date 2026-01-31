from odoo import http
from odoo.http import request
import json

class DebugInventoryController(http.Controller):
    
    @http.route('/debug/inventory', type='http', auth='user')
    def debug_inventory(self, **kwargs):
        env = request.env
        
        output = []
        output.append("<h1>Inventory Debug Information</h1>")
        
        # 1. Check Product Model
        output.append("<h2>1. Product Model Fields</h2>")
        product_model = env['product.product']
        output.append(f"<p>Model: product.product</p>")
        
        # Get all fields
        product_fields = product_model.fields_get()
        output.append("<p>Important fields for inventory:</p>")
        output.append("<ul>")
        for field_name, field_info in product_fields.items():
            if any(keyword in field_name.lower() for keyword in ['qty', 'stock', 'available', 'quantity', 'value']):
                output.append(f"<li><strong>{field_name}</strong>: {field_info.get('type', 'N/A')} - {field_info.get('string', 'N/A')}</li>")
        output.append("</ul>")
        
        # Check specific fields
        output.append("<p>Checking specific fields:</p>")
        test_product = env['product.product'].search([('type', '=', 'product')], limit=1)
        if test_product:
            output.append(f"<p>Test Product: {test_product.name}</p>")
            fields_to_check = ['qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty', 'stock_value', 'value_svl', 'standard_price']
            for field in fields_to_check:
                if hasattr(test_product, field):
                    try:
                        value = getattr(test_product, field)
                        output.append(f"<p>✓ {field}: {value}</p>")
                    except:
                        output.append(f"<p>✗ {field}: Error accessing</p>")
                else:
                    output.append(f"<p>✗ {field}: Does not exist</p>")
        
        # 2. Check Stock Move Model
        output.append("<h2>2. Stock Move Model Fields</h2>")
        try:
            move_model = env['stock.move']
            move_fields = move_model.fields_get()
            output.append("<p>Important fields for stock moves:</p>")
            output.append("<ul>")
            for field_name, field_info in move_fields.items():
                if any(keyword in field_name.lower() for keyword in ['qty', 'quantity', 'done', 'product', 'state']):
                    output.append(f"<li><strong>{field_name}</strong>: {field_info.get('type', 'N/A')} - {field_info.get('string', 'N/A')}</li>")
            output.append("</ul>")
            
            # Test a stock move
            test_move = env['stock.move'].search([], limit=1)
            if test_move:
                output.append(f"<p>Test Move: {test_move.name or 'No name'}</p>")
                move_fields_to_check = ['quantity_done', 'product_qty', 'quantity', 'reserved_availability', 'availability', 'state']
                for field in move_fields_to_check:
                    if hasattr(test_move, field):
                        try:
                            value = getattr(test_move, field)
                            output.append(f"<p>✓ {field}: {value}</p>")
                        except:
                            output.append(f"<p>✗ {field}: Error accessing</p>")
                    else:
                        output.append(f"<p>✗ {field}: Does not exist</p>")
        except Exception as e:
            output.append(f"<p>Error accessing stock.move: {str(e)}</p>")
        
        # 3. Check actual data
        output.append("<h2>3. Actual Inventory Data</h2>")
        
        # Products with stock
        products_with_stock = env['product.product'].search([
            ('type', '=', 'product'),
        ])
        output.append(f"<p>Total products: {len(products_with_stock)}</p>")
        
        output.append("<table border='1'><tr><th>Product</th><th>Fields Available</th><th>Values</th></tr>")
        for product in products_with_stock[:10]:  # First 10 products
            fields_info = []
            values_info = []
            
            # Check different field names
            possible_qty_fields = ['qty_available', 'virtual_available', 'free_qty']
            possible_value_fields = ['stock_value', 'value_svl', 'standard_price']
            
            for field in possible_qty_fields:
                if hasattr(product, field):
                    try:
                        value = getattr(product, field)
                        fields_info.append(field)
                        values_info.append(f"{field}: {value}")
                    except:
                        pass
            
            for field in possible_value_fields:
                if hasattr(product, field):
                    try:
                        value = getattr(product, field)
                        fields_info.append(field)
                        values_info.append(f"{field}: {value}")
                    except:
                        pass
            
            output.append(f"<tr><td>{product.name}</td><td>{', '.join(fields_info)}</td><td>{'<br>'.join(values_info)}</td></tr>")
        output.append("</table>")
        
        # Stock moves
        output.append("<h3>Recent Stock Moves</h3>")
        try:
            recent_moves = env['stock.move'].search([], limit=10, order='id desc')
            output.append(f"<p>Recent moves: {len(recent_moves)}</p>")
            
            output.append("<table border='1'><tr><th>Move</th><th>Product</th><th>State</th><th>Quantity Fields</th></tr>")
            for move in recent_moves:
                qty_info = []
                for field in ['quantity_done', 'product_qty', 'quantity', 'reserved_availability']:
                    if hasattr(move, field):
                        try:
                            value = getattr(move, field)
                            qty_info.append(f"{field}: {value}")
                        except:
                            pass
                
                output.append(f"<tr><td>{move.name or 'N/A'}</td><td>{move.product_id.name if move.product_id else 'N/A'}</td><td>{move.state}</td><td>{'<br>'.join(qty_info)}</td></tr>")
            output.append("</table>")
        except Exception as e:
            output.append(f"<p>Error getting stock moves: {str(e)}</p>")
        
        return ''.join(output)