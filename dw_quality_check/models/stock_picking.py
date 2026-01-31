from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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
        string="Quality Check Passed",
        compute='_compute_quality_check_passed_delivery',
        store=True,
        readonly=True,
        help="True if the source (manufacturing or purchase receipt) passed quality check."
    )

    @api.depends('state', 'picking_type_id', 'qc_state')
    def _compute_show_qc_button(self):
        for rec in self:
            rec.show_qc_button = (
                rec.state == 'done'
                and rec.picking_type_id.code == 'incoming'
                and rec.qc_state == 'not_required'
            )

    @api.depends(
        'picking_type_code',
        'origin',
        'state',
        'move_ids_without_package.move_orig_ids.production_id.qc_state',
    )
    def _compute_quality_check_passed_delivery(self):
        _logger.warning("=== QC COMPUTE STARTED for %d pickings ===", len(self))

        for picking in self:
            _logger.warning(
                "QC DEBUG - Picking: %s | ID: %s | Type: %s | Origin: %s | State: %s",
                picking.name or "No name", picking.id, picking.picking_type_code, 
                picking.origin or "No origin", picking.state
            )

            if picking.picking_type_code != 'outgoing':
                picking.quality_check_passed = False
                _logger.warning("  → Not outgoing → set False")
                continue

            passed = False

            # 1. MO flow
            source_mos = self.env['mrp.production'].search([
                ('origin', '=', picking.origin),
                ('state', '=', 'done'),
            ])
            _logger.warning("  → MO search: %d found | Names: %s", len(source_mos), source_mos.mapped('name') or ['NONE'])
            if source_mos:
                qc_states = source_mos.mapped('qc_state')
                _logger.warning("  → MO QC states: %s", qc_states)
                relevant = source_mos.filtered(lambda m: m.qc_state != 'not_required')
                if all(m.qc_state == 'passed' for m in relevant) and len(relevant) > 0:
                    passed = True
                    _logger.warning("  → MO flow → PASSED")
                else:
                    _logger.warning("  → MO flow → NOT passed")

            # 2. PO flow with detailed debug
            if not passed and picking.origin:
                sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                _logger.warning("  → SO search for origin '%s': %s (ID %s)",
                                picking.origin, "FOUND" if sale_order else "NOT FOUND",
                                sale_order.id if sale_order else "N/A")

                if sale_order:
                    purchase_orders = self.env['purchase.order'].search([
                        '|',
                        ('origin', '=', sale_order.name),
                        ('order_line.sale_line_id.order_id', '=', sale_order.id),
                        ('state', 'in', ('purchase', 'done')),
                    ])
                    _logger.warning("  → POs found: %d | Names: %s", len(purchase_orders), purchase_orders.mapped('name') or ['NONE'])

                    if purchase_orders:
                        incoming_pickings = self.env['stock.picking'].search([
                            ('purchase_id', 'in', purchase_orders.ids),
                            ('picking_type_code', 'in', ('incoming', 'internal')),
                            ('state', '=', 'done'),
                        ])
                        _logger.warning("  → Incoming pickings: %d | Names: %s", len(incoming_pickings), incoming_pickings.mapped('name') or ['NONE'])

                        if incoming_pickings:
                            states = incoming_pickings.mapped('qc_state')
                            _logger.warning("  → Incoming QC states: %s", states)
                            relevant = incoming_pickings.filtered(lambda p: p.qc_state != 'not_required')
                            if all(p.qc_state == 'passed' for p in relevant) and len(relevant) > 0:
                                passed = True
                                _logger.warning("  → PO flow → PASSED")
                            else:
                                _logger.warning("  → PO flow → NOT passed (states not all 'passed')")
                        else:
                            _logger.warning("  → No incoming pickings found")
                    else:
                        _logger.warning("  → No POs linked to SO")
                else:
                    _logger.warning("  → No SO found for origin")

            # Fallback: if no link found, check if any incoming done picking has passed QC for same product
            if not passed:
                _logger.warning("  → Trying fallback product match...")
                product_ids = picking.move_ids_without_package.mapped('product_id').ids
                if product_ids:
                    fallback_incoming = self.env['stock.picking'].search([
                        ('move_ids_without_package.product_id', 'in', product_ids),
                        ('picking_type_code', 'in', ('incoming', 'internal')),
                        ('state', '=', 'done'),
                        ('qc_state', '=', 'passed'),
                    ], limit=1)
                    _logger.warning("  → Fallback incoming with passed QC: %s", fallback_incoming.name or "NONE")
                    if fallback_incoming:
                        passed = True
                        _logger.warning("  → Fallback → PASSED")

            picking.quality_check_passed = passed
            _logger.warning("  → FINAL RESULT for %s: %s", picking.name, passed)

        _logger.warning("=== QC COMPUTE FINISHED ===")
        
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