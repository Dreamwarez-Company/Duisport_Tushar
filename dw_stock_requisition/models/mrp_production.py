from odoo import models, fields, api, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_create_requisition(self):
        """Create a requisition from manufacturing order"""
        self.ensure_one()
        
        # Create requisition with MO reference
        requisition_vals = {
            'manufacturing_order_id': self.id,
            'date': fields.Date.today(),
            'department': 'store',  # Set department to 'store' by default
            'required_date': self.date_start.date() if self.date_start else fields.Date.today(),
            'source_location_id': self.location_src_id.id if self.location_src_id else False,
            'destination_location_id': self.product_id.property_stock_production.id if self.product_id else False,
        }
        
        requisition = self.env['dw.mrp.requisition'].create(requisition_vals)
        
        # Add components to requisition lines
        for move in self.move_raw_ids:
            line_vals = {
                'requisition_id': requisition.id,
                'product_id': move.product_id.id,
                'quantity': move.product_uom_qty,
                'uom_id': move.product_uom.id,
            }
            self.env['dw.mrp.requisition.line'].create(line_vals)
        
        # Use the unified form view, which adapts based on user groups
        view_id = self.env.ref('dw_stock_requisition.view_dw_mrp_requisition_form').id
        
        # Return action to open the created requisition
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dw.mrp.requisition',
            'res_id': requisition.id,
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
        }
    
    