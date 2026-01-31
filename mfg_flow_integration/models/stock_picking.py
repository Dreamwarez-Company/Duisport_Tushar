from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_print_challan(self):
        return self.env.ref('mfg_flow_integration.report_delivery_challan').report_action(self)
    
    def button_validate(self):
        for picking in self:
            res = super().button_validate()

            # Only handle Incoming Receipts
            if picking.picking_type_code != 'incoming':
                continue

            # Get PO from picking lines
            purchase_orders = picking.move_ids_without_package.mapped('purchase_line_id.order_id')
            purchase_order = purchase_orders[:1]

            if not purchase_order:
                _logger.warning("NO PO FOUND for picking %s - Cannot log time tracking", picking.name)
                continue

            # Get Sale Order for lead
            sale_order = self.env['sale.order'].search([
                ('name', '=', purchase_order.origin)
            ], limit=1)
            lead_id = sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False

            # ---------------------------------------------------------
            # 1️⃣ CLOSE PREVIOUS STAGE → "Incoming Receipt Created"
            # ---------------------------------------------------------
            last_receipt_track = self.env['department.time.tracking'].search([
                ('target_model', '=', f'stock.picking,{picking.id}'),
                ('status', '=', 'in_progress'),
                ('stage_name', '=', 'Incoming Receipt Created')
            ], limit=1, order='start_time desc')

            if last_receipt_track:
                last_receipt_track.write({
                    'end_time': fields.Datetime.now(),
                    'status': 'done',
                })

            # ---------------------------------------------------------
            # 2️⃣ CREATE NEW STAGE → "PO Received/Validated"
            # ---------------------------------------------------------
            self.env['department.time.tracking'].create({
                'target_model': f'purchase.order,{purchase_order.id}',
                'stage_name': 'PO Received/Validated',
                'user_id': self.env.user.id,
                'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'start_time': fields.Datetime.now(),
                'status': 'in_progress',
                'lead_id': lead_id,
            })

        return res


