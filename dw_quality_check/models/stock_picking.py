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
        store=True
    )
    quality_check_passed = fields.Boolean(
        string="Quality Check",
        readonly=True
    )


    @api.depends('state', 'picking_type_id', 'qc_state')
    def _compute_show_qc_button(self):
        for rec in self:
            rec.show_qc_button = (
                rec.state == 'done'
                and rec.picking_type_id.code == 'incoming'
                and rec.qc_state == 'not_required'
            )
            
    # def action_send_for_qc(self):
    #     """Triggered from receipts or internal transfers after validation"""
    #     for picking in self:
    #         picking_type = picking.picking_type_id.code

    #         if picking_type not in ['incoming', 'internal']:
    #             raise UserError('Quality check can only be performed for incoming or internal transfers.')

    #         for move in picking.move_ids_without_package:
    #             qty_done = sum(move.move_line_ids.mapped('quantity'))
    #             if qty_done <= 0:
    #                 continue

    #             lot_id = False
    #             if move.product_id.tracking == 'lot':
    #                 lot_id = move.move_line_ids[:1].lot_id.id or False

    #             self.env['dw.quality.check'].create({
    #                 'picking_id': picking.id,
    #                 'product_id': move.product_id.id,
    #                 'quantity': qty_done,
    #                 'lot_id': lot_id,
    #             })

    #         # ✅ Hide the button after QC is sent
    #         picking.show_qc_button = False

    #         picking.message_post(
    #             body=f"Quality Check initiated for {picking_type} transfer.",
    #             message_type="comment",
    #             subtype_xmlid="mail.mt_comment"
    #         )

    #         picking.qc_state = 'pending'

    #     if self.env.user.has_group('dw_quality_check.group_quality_check'):
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': 'Quality Checks',
    #             'res_model': 'dw.quality.check',
    #             'view_mode': 'tree,form',
    #             'domain': [('picking_id', '=', self.id)],
    #             'target': 'current',
    #         }
    #     else:
    #         return {
    #             'effect': {
    #                 'fadeout': 'slow',
    #                 'message': 'Quality Check has been sent to QC team.',
    #                 'type': 'rainbow_man',
    #             }
    #         }


    def action_send_for_qc(self):
        """Triggered from receipts or internal transfers after validation"""
        for picking in self:
            picking_type = picking.picking_type_id.code

            if picking_type not in ['incoming', 'internal']:
                raise UserError('Quality check can only be performed for incoming or internal transfers.')

            # -------------------------------------------
            # CREATE QC RECORDS
            # -------------------------------------------
            for move in picking.move_ids_without_package:
                qty_done = sum(move.move_line_ids.mapped('quantity'))
                if qty_done <= 0:
                    continue

                lot_id = False
                if move.product_id.tracking == 'lot':
                    lot_id = move.move_line_ids[:1].lot_id.id or False

                self.env['dw.quality.check'].create({
                    'picking_id': picking.id,
                    'product_id': move.product_id.id,
                    'quantity': qty_done,
                    'lot_id': lot_id,
                })

            picking.show_qc_button = False
            picking.qc_state = 'pending'

            picking.message_post(
                body=f"Quality Check initiated for {picking_type} transfer.",
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )

            # -------------------------------------------------------------------
            # TIME TRACKING — QC INITIATED
            # -------------------------------------------------------------------
            purchase_orders = picking.move_ids_without_package.mapped(
                "purchase_line_id.order_id"
            )
            purchase_order = purchase_orders[:1]

            sale_order = False
            if purchase_order and purchase_order.origin:
                sale_order = self.env["sale.order"].search(
                    [("name", "=", purchase_order.origin)], limit=1
                )

            # Close previous GRN stage
            last_track = self.env["department.time.tracking"].search(
                [
                    ("target_model", "=", f"purchase.order,{purchase_order.id}"),
                    ("status", "=", "in_progress"),
                ],
                limit=1, order="start_time desc"
            )

            if last_track:
                last_track.write({
                    "end_time": fields.Datetime.now(),
                    "status": "done"
                })

            # Create new QC stage
            self.env["department.time.tracking"].create({
                "target_model": f"purchase.order,{purchase_order.id}",
                "stage_name": "QC Initiated",
                "user_id": self.env.user.id,
                "employee_id": self.env.user.employee_id.id if self.env.user.employee_id else False,
                "start_time": fields.Datetime.now(),
                "status": "in_progress",
                "lead_id": sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False,
            })

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

