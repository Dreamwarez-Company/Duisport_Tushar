from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # ------------------------------------------------------------
    # DELIVERY INITIATED (Check Availability)
    # ------------------------------------------------------------
    def action_assign(self):
        res = super().action_assign()

        outgoing = self.filtered(lambda p: p.picking_type_code == "outgoing")

        for picking in outgoing:

            # SALE ORDER → LEAD
            sale_order = self.env["sale.order"].search([
                ("name", "=", picking.origin)
            ], limit=1)

            lead_id = sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False

            # CREATE Delivery Initiated
            self.env["department.time.tracking"].create({
                "target_model": f"stock.picking,{picking.id}",
                "stage_name": "Delivery Initiated",
                "user_id": self.env.user.id,
                "employee_id": self.env.user.employee_id.id if self.env.user.employee_id else False,
                "start_time": fields.Datetime.now(),
                "status": "in_progress",
                "lead_id": lead_id,
            })

        return res

    # ------------------------------------------------------------
    # DELIVERY DONE/VALIDATED (Validate button)
    # ------------------------------------------------------------
    def button_validate(self):
        outgoing = self.filtered(lambda p: p.picking_type_code == "outgoing")

        res = super().button_validate()

        for picking in outgoing:

            sale_order = self.env["sale.order"].search([
                ("name", "=", picking.origin)
            ], limit=1)

            lead_id = sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False

            # CLOSE Delivery Initiated
            last_stage = self.env["department.time.tracking"].search([
                ('target_model', '=', f'stock.picking,{picking.id}'),
                ('stage_name', '=', 'Delivery Initiated'),
                ('status', '=', 'in_progress'),
            ], limit=1, order="start_time desc")

            if last_stage:
                last_stage.write({
                    "end_time": fields.Datetime.now(),
                    "status": "done"
                })

            # CREATE Delivery Done
            self.env["department.time.tracking"].create({
                "target_model": f"stock.picking,{picking.id}",
                "stage_name": "Delivery Done/Validated",
                "user_id": self.env.user.id,
                "employee_id": self.env.user.employee_id.id if self.env.user.employee_id else False,
                "start_time": fields.Datetime.now(),
                "end_time": fields.Datetime.now(),
                "status": "done",
                "lead_id": lead_id,
            })

        return res
