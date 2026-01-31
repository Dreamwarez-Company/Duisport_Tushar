from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    qc_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='QC State', default='not_required', compute='_compute_qc_state', store=True)

    show_qc_button = fields.Boolean(
        string="Show QC Button",
        compute="_compute_show_qc_button",
        store=False
    )

    @api.depends('state', 'picking_type_id')
    def _compute_show_qc_button(self):
        for rec in self:
            rec.show_qc_button = (
                rec.state == 'done' and
                rec.picking_type_id.code == 'incoming'
            )
            
    def action_send_for_qc(self):
        """Triggered from receipts or internal transfers after validation"""
        for picking in self:
            picking_type = picking.picking_type_id.code

            # Allow QC for incoming or internal transfers
            if picking_type not in ['incoming', 'internal']:
                raise UserError('Quality check can only be performed for incoming or internal transfers.')

            # Create QC records for each product in the picking
            for move in picking.move_ids_without_package:
                qty_done = sum(move.move_line_ids.mapped('quantity'))
                if qty_done <= 0:
                    continue

                # ✅ Determine lot safely based on tracking type
                lot_id = False
                if move.product_id.tracking == 'lot':
                    # Assign lot if product uses lot tracking
                    lot_id = move.move_line_ids[:1].lot_id.id or False
                # ⚠️ Skip serial tracking (do not assign lot/serial)
                # to avoid duplicate serial assignment errors

                # ✅ Create Quality Check record safely
                self.env['dw.quality.check'].create({
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'quantity': qty_done,
                    'lot_id': lot_id,  # safe for lot-tracked products
                })

            # ✅ Log activity to chatter only (no email)
            picking.message_post(
                body=f"Quality Check initiated for {picking_type} transfer.",
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )
            picking.qc_state = 'pending'

        # ✅ Only QC group members see the QC records
        if self.env.user.has_group('dw_quality_check.group_quality_check'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quality Checks',
                'res_model': 'dw.quality.check',
                'view_mode': 'tree,form',
                'domain': [('picking_id', '=', self.id)],
                'target': 'current',
            }
        else:
            # ✅ Inventory users just get a success animation
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Quality Check has been sent to QC team.',
                    'type': 'rainbow_man',
                }
            }

    def action_done(self):
        # prevent validation if QC failed or pending depending on your policy
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                if picking.qc_state == 'failed':
                    raise UserError('QC failed for this receipt. Please resolve QC before validating the transfer.')
                if picking.qc_state == 'pending':
                    # Option: block; here we block by default
                    raise UserError('QC is pending for this receipt. Please perform QC before validating the transfer.')
        return super().action_done()
    
    def action_set_failed(self):
        for rec in self:
            rec.status = 'failed'
            rec.passed = False
            rec._update_picking_qc_state()
            rec.message_post(body=f'QC {rec.name} marked as Failed by {self.env.user.name}')
            rec._create_return_request()

    def _create_return_request(self):
        """Automatically create a return picking when QC fails."""
        for rec in self:
            picking = rec.picking_id
            if not picking:
                continue

            # Determine return picking type
            if picking.picking_type_id.code == 'incoming':
                # Return to supplier
                return_type = picking.picking_type_id.return_picking_type_id or picking.picking_type_id
            elif picking.picking_type_id.code == 'internal':
                # Return to store (reverse locations)
                return_type = picking.picking_type_id
            else:
                continue

            # Create return picking
            return_picking = picking.copy({
                'origin': f"Return for {picking.name} (QC Failed)",
                'picking_type_id': return_type.id,
                'move_ids_without_package': [],
            })

            # Move from destination back to source
            self.env['stock.move'].create({
                'name': f'Return {rec.product_id.display_name}',
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.quantity,
                'product_uom': rec.product_id.uom_id.id,
                'picking_id': return_picking.id,
                'location_id': picking.location_dest_id.id,
                'location_dest_id': picking.location_id.id,
            })

            return_picking.action_confirm()
            picking.message_post(
                body=f"Return {return_picking.name} created for failed QC {rec.name}."
            )

