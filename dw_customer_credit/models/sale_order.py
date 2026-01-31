from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
    exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
    available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    
    @api.depends('partner_id', 'amount_total')
    def _compute_credit_check_required(self):
        for order in self:
            order.credit_check_required = bool(order.partner_id.credit_limit > 0)
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit', 'partner_id.credit_limit_reached')
    def _compute_credit_limit(self):
        for order in self:
            if order.partner_id.credit_limit > 0:
                partner = order.partner_id
                
                # Calculate total from posted invoices (using amount_residual for accurate unpaid amount)
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                total_unpaid = sum(posted_invoices.mapped('amount_residual'))
                
                # Calculate total from confirmed sales orders that are NOT fully invoiced
                confirmed_orders = self.env['sale.order'].search([
                    ('partner_id', '=', partner.id),
                    ('state', '=', 'sale'),
                    ('id', '!=', order.id if order.id else False)
                ])
                
                # Only include orders that are not fully invoiced
                orders_not_invoiced = 0
                for so in confirmed_orders:
                    if so.invoice_status != 'invoiced' or so.amount_total > so.amount_invoiced:
                        orders_not_invoiced += so.amount_total - so.amount_invoiced
                
                # Calculate net outstanding (unpaid invoices + uninvoiced portion of confirmed orders)
                net_outstanding = total_unpaid + orders_not_invoiced
                current_order_amount = order.amount_total if order.state != 'cancel' else 0
                
                # Total including current order
                total_with_current = net_outstanding + current_order_amount
                
                order.available_credit = max(0, order.partner_id.credit_limit - total_with_current)
                order.exceeds_credit_limit = total_with_current > order.partner_id.credit_limit
                
                _logger.info(
                    f"=== CREDIT CALCULATION FOR {partner.name} ===\n"
                    f"Credit Limit: {order.partner_id.credit_limit}\n"
                    f"Unpaid Invoices: {total_unpaid}\n"
                    f"Uninvoiced Orders: {orders_not_invoiced}\n"
                    f"Net Outstanding: {net_outstanding}\n"
                    f"Current Order: {current_order_amount}\n"
                    f"Total With Current: {total_with_current}\n"
                    f"Available Credit: {order.available_credit}\n"
                    f"Exceeds Limit: {order.exceeds_credit_limit}\n"
                    f"======================================"
                )
            else:
                order.available_credit = 0
                order.exceeds_credit_limit = False

    def _check_credit_limit(self):
        """Reusable credit limit check for quotation creation & confirmation"""
        for order in self:
            if order.partner_id.credit_limit > 0:
                partner = order.partner_id
                
                # Calculate total from posted invoices (using amount_residual for accurate unpaid amount)
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                total_unpaid = sum(posted_invoices.mapped('amount_residual'))
                
                # Calculate total from confirmed sales orders that are NOT fully invoiced
                confirmed_orders = self.env['sale.order'].search([
                    ('partner_id', '=', partner.id),
                    ('state', '=', 'sale'),
                    ('id', '!=', order.id if order.id else False)
                ])
                
                # Only include orders that are not fully invoiced
                orders_not_invoiced = 0
                for so in confirmed_orders:
                    if so.invoice_status != 'invoiced' or so.amount_total > so.amount_invoiced:
                        orders_not_invoiced += so.amount_total - so.amount_invoiced
                
                # Calculate net outstanding
                net_outstanding = total_unpaid + orders_not_invoiced
                total_with_current = net_outstanding + order.amount_total
                
                if total_with_current > order.partner_id.credit_limit:
                    raise UserError(
                        f"This quotation exceeds {order.partner_id.name}'s credit limit.\n"
                        f"Credit Limit: {order.partner_id.credit_limit}\n"
                        f"Current Outstanding (Unpaid Invoices + Uninvoiced Orders): {net_outstanding}\n"
                        f"Quotation Amount: {order.amount_total}\n"
                        f"Total After Quotation: {total_with_current}\n"
                        f"Available Credit: {max(0, order.partner_id.credit_limit - net_outstanding)}\n\n"
                        f"Please request customer payment or contact sales manager."
                    )

    def create(self, vals):
        order = super(SaleOrder, self).create(vals)
        order._check_credit_limit()
        return order

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self._check_credit_limit()
        return res

    def action_confirm(self):
        self._check_credit_limit()
        return super(SaleOrder, self).action_confirm()