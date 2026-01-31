from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    cost_price = fields.Float("Cost Price")
    cost_price_mgnt = fields.Float("Cost Price M")
    design_ref = fields.Binary("Design Reference")
    design_ref_filename = fields.Char("Design Reference Filename")
    estimation_time = fields.Float("Estimation Time (hrs)")
    engineering_notes = fields.Text("Engineering Notes")
    
    bom_ids = fields.One2many(
        'mrp.bom',
        'product_tmpl_id',
        string="Bill of Materials"
    )


    def action_analysis_done(self):
            
            
            # Show confirmation message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Analysis Completed',
                    'message': 'Product analysis has been marked as done.',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
    def action_open_engineering_team(self):
        """Open Engineering Team view from product form"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Engineering Team - ' + self.name,
            'res_model': 'product.template',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('dw_engineering_team.view_engineering_team_form').id,
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    
    def action_open_product_form(self):
        """Open main product form from Engineering Team view"""
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'product.template',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('product.product_template_form_view').id,
            'target': 'current',
        }

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'
    
    product_availability = fields.Char(
        string="Availability",
        compute='_compute_product_availability',
        store=False
    )
    
    @api.depends('product_id', 'product_qty')
    def _compute_product_availability(self):
        for line in self:
            if line.product_id:
                # Get the available quantity (on hand - reserved)
                available_qty = line.product_id.qty_available - line.product_id.outgoing_qty
                
                if available_qty >= line.product_qty:
                    line.product_availability = "Available"
                elif available_qty > 0:
                    line.product_availability = f"Low Stock ({available_qty})"
                else:
                    line.product_availability = "Out of Stock"
            else:
                line.product_availability = "No Product"


class MrpBom(models.Model):
    _inherit = 'mrp.bom'
    
    availability_status = fields.Char(
        string="Overall Availability",
        compute='_compute_availability_status',
        store=False
    )
    
    @api.depends('bom_line_ids.product_availability')
    def _compute_availability_status(self):
        for bom in self:
            if not bom.bom_line_ids:
                bom.availability_status = "Unknown"
                continue
            
            line_statuses = [line.product_availability for line in bom.bom_line_ids]
            
            if all("Available" in status for status in line_statuses):
                bom.availability_status = "Available"
            elif any("Out of Stock" in status for status in line_statuses):
                bom.availability_status = "Not Available"
            elif any("Low Stock" in status for status in line_statuses):
                bom.availability_status = "Partially Available"
            else:
                bom.availability_status = "Unknown"





