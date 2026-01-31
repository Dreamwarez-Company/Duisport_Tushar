from odoo import api, fields,models
from odoo.exceptions import UserError

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    material_checked = fields.Boolean(string="Material Checked", default=False)
    

    def action_check_material(self):
        for mo in self:
            if not mo.bom_id:
                raise UserError("No BOM found for this MO.")

            shortage_products = []
            purchase_order_lines = []
            vendor = self.env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)  # default vendor

            for line in mo.bom_id.bom_line_ids:
                product = line.product_id
                required_qty = line.product_qty * mo.product_qty
                available_qty = product.qty_available

                if available_qty < required_qty:
                    shortage = required_qty - available_qty
                    shortage_products.append((product.display_name, shortage))

                    purchase_order_lines.append((0, 0, {
                        'product_id': product.id,
                        'product_qty': shortage,
                        'product_uom': product.uom_id.id,
                        'price_unit': product.standard_price,
                        'name': f"Auto purchase for {mo.name}"
                    }))

            if shortage_products:
                po = self.env['purchase.order'].create({
                    'partner_id': vendor.id,
                    'origin': mo.name,
                    'order_line': purchase_order_lines,
                })
                mo.message_post(body=f"Shortage detected. RFQ/PO <b>{po.name}</b> created.")
            else:
                mo.message_post(body="All required materials are available in stock. No RFQ/PO created.")

            mo.material_checked = True


    def button_mark_done(self):
        res = super().button_mark_done()
        for mo in self:
            # try find sale order by origin
            if mo.origin:
                sale_order = self.env['sale.order'].search([('name', '=', mo.origin)], limit=1)
                if sale_order:
                    # create invoice from sale order lines (simple version)
                    invoice_vals = {
                        'move_type': 'out_invoice',
                        'partner_id': sale_order.partner_id.id,
                        'invoice_origin': sale_order.name,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': line.product_id.id,
                            'quantity': line.product_uom_qty,
                            'price_unit': line.price_unit,
                        }) for line in sale_order.order_line],
                    }
                    invoice = self.env['account.move'].create(invoice_vals)
                    
                    mo.message_post(body=f"Draft Invoice <b>{invoice.name}</b> created from MO completion.")
        return res
