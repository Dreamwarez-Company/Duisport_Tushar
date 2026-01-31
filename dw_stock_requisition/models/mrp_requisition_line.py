from odoo import models, fields, api

class MrpRequisitionLine(models.Model):
    _name = 'dw.mrp.requisition.line'
    _description = 'Manufacturing Requisition Line Items'
    
    sequence = fields.Integer(string='Sequence', default=10)
    requisition_id = fields.Many2one(
        'dw.mrp.requisition',
        string='Requisition'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    description = fields.Char(string='Description')
    quantity = fields.Float(
        string='Quantity',
        default=1.0 
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    available_qty = fields.Float(
        string='Available Quantity',
        compute='_compute_available_qty'
    )
    notes = fields.Char(string='Line Notes')
    
    @api.depends('product_id', 'requisition_id.source_location_id', 'requisition_id.requested_location_id', 'requisition_id.state')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id:
                location = False
                
                # If state is 'requested_other_location', use requested_location_id
                if line.requisition_id.state == 'requested_other_location' and line.requisition_id.requested_location_id:
                    location = line.requisition_id.requested_location_id
                # For other states, use source_location_id
                elif line.requisition_id.source_location_id:
                    location = line.requisition_id.source_location_id
                
                if location:
                    # Calculate available quantity in the specific location
                    line.available_qty = line.product_id.with_context(
                        location=location.id
                    ).qty_available
                else:
                    line.available_qty = 0.0
            else:
                line.available_qty = 0.0
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id