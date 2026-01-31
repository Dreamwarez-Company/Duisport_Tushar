from odoo import api, models, fields

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def create(self, vals):
        # If product provided and partner not set, pick best vendor (lowest price)
        if vals.get('product_id') and not vals.get('partner_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            # use supplierinfo (seller_ids) for vendor info
            sellers = product.seller_ids.sorted(key=lambda s: s.price or 0.0)
            if sellers:
                best = sellers[0]
                vals['partner_id'] = best.partner_id.id
                vals['price_unit'] = best.price or vals.get('price_unit', 0.0)
        return super().create(vals)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # def button_confirm(self):
    #     # ensure lines have vendor & computed price before confirm
    #     for order in self:
    #         for line in order.order_line:
    #             if line.product_id and not line.partner_id:
    #                 sellers = line.product_id.seller_ids.sorted(key=lambda s: s.price or 0.0)
    #                 if sellers:
    #                     best = sellers[0]
    #                     line.partner_id = best.name.id
    #                     line.price_unit = best.price or line.price_unit
    #     return super().button_confirm()

    def button_confirm(self):
        for po in self:

            # ---------------------------------------------------
            # AUTO ASSIGN BEST VENDOR
            # ---------------------------------------------------
            for line in po.order_line:
                if line.product_id and not line.partner_id:
                    sellers = line.product_id.seller_ids.sorted(key=lambda s: s.price or 0.0)
                    if sellers:
                        best = sellers[0]
                        line.partner_id = best.name.id
                        line.price_unit = best.price or line.price_unit

            # ---------------------------------------------------
            # FIND RELATED RECORDS (Production Request & Lead)
            # ---------------------------------------------------
            production_request = self.env['production.request'].search([
                ('purchase_order_ids', 'in', po.id)
            ], limit=1)

            sale_order = self.env['sale.order'].search([
                ('name', '=', po.origin)
            ], limit=1)

            lead_id = sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False

            # ---------------------------------------------------
            # 1️⃣ CLOSE PREVIOUS TRACK ("PO Created")
            # ---------------------------------------------------
            if production_request:
                last_track = self.env['department.time.tracking'].search([
                    ('target_model', '=', f'production.request,{production_request.id}'),
                    ('status', '=', 'in_progress'),
                    ('stage_name', '=', 'PO Created')
                ], limit=1, order='start_time desc')

                if last_track:
                    last_track.write({
                        'end_time': fields.Datetime.now(),
                        'status': 'done',
                    })

                # ---------------------------------------------------
                # 2️⃣ CREATE NEW TRACK → "PO Confirmed"
                # ---------------------------------------------------
                self.env['department.time.tracking'].create({
                    'target_model': f'purchase.order,{po.id}',
                    'stage_name': 'PO Confirmed',
                    'user_id': self.env.user.id,
                    'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'start_time': fields.Datetime.now(),
                    'status': 'in_progress',
                    'lead_id': lead_id,
                })

        # ---------------------------------------------------------
        # CALL ORIGINAL CONFIRM
        # ---------------------------------------------------------
        res = super(PurchaseOrder, self).button_confirm()

        # ---------------------------------------------------------
        # 3️⃣ CLOSE "PO Confirmed" AND CREATE "Incoming Receipt Created"
        # ---------------------------------------------------------
        for po in self:

            sale_order = self.env['sale.order'].search([
                ('name', '=', po.origin)
            ], limit=1)

            lead_id = sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False

            picking = self.env['stock.picking'].search([
                ('origin', '=', po.name),
                ('picking_type_code', '=', 'incoming')
            ], limit=1)

            if picking:

                # CLOSE PO Confirmed
                last_po_confirm_track = self.env['department.time.tracking'].search([
                    ('target_model', '=', f'purchase.order,{po.id}'),
                    ('status', '=', 'in_progress'),
                    ('stage_name', '=', 'PO Confirmed')
                ], limit=1, order='start_time desc')

                if last_po_confirm_track:
                    last_po_confirm_track.write({
                        'end_time': fields.Datetime.now(),
                        'status': 'done'
                    })

                # CREATE Incoming Receipt Created
                self.env['department.time.tracking'].create({
                    'target_model': f'stock.picking,{picking.id}',
                    'stage_name': 'Incoming Receipt Created',
                    'user_id': self.env.user.id,
                    'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'start_time': fields.Datetime.now(),
                    'status': 'in_progress',
                    'lead_id': lead_id,
                })

        return res
