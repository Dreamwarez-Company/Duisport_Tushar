from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    credit_check_required = fields.Boolean(string='Credit Check Required', compute='_compute_credit_check_required')
    exceeds_credit_limit = fields.Boolean(string='Exceeds Credit Limit', compute='_compute_credit_limit')
    available_credit = fields.Float(string='Available Credit', compute='_compute_credit_limit')
    lr_date = fields.Date(string='LR Date')
    lr_no = fields.Date(string='LR Date')
    transporter = fields.Date(string='LR Date')
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit')
    def _compute_credit_check_required(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move.credit_check_required = bool(move.partner_id.credit_limit > 0)
            else:
                move.credit_check_required = False
    
    @api.depends('partner_id', 'amount_total', 'partner_id.credit_limit', 'partner_id.credit_limit_reached')
    def _compute_credit_limit(self):
        for move in self:
            if move.move_type == 'out_invoice' and move.partner_id.credit_limit > 0:
                # Calculate total outstanding invoices (amount_total of posted invoices)
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('id', '!=', move.id if move.id else False)
                ])
                total_invoiced = sum(posted_invoices.mapped('amount_total'))
                
                # Calculate total payments received from customer
                # Better approach: Use account.payment model directly
                payments = self.env['account.payment'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('state', '=', 'posted'),
                    ('payment_type', '=', 'inbound')
                ])
                total_payments = sum(payments.mapped('amount'))
                
                # Calculate net outstanding (invoiced - payments)
                net_outstanding = total_invoiced - total_payments
                current_invoice_amount = move.amount_total if move.state != 'cancel' else 0
                
                # Total including current invoice
                total_with_current = net_outstanding + current_invoice_amount
                
                move.available_credit = max(0, move.partner_id.credit_limit - total_with_current)
                move.exceeds_credit_limit = total_with_current > move.partner_id.credit_limit
                
                _logger.info(
                    f"Invoice {move.name}: partner={move.partner_id.name}, "
                    f"credit_limit={move.partner_id.credit_limit}, "
                    f"total_invoiced={total_invoiced}, "
                    f"total_payments={total_payments}, "
                    f"net_outstanding={net_outstanding}, "
                    f"current_invoice={current_invoice_amount}, "
                    f"total_with_current={total_with_current}, "
                    f"available_credit={move.available_credit}, "
                    f"exceeds_credit_limit={move.exceeds_credit_limit}"
                )
            else:
                move.available_credit = 0
                move.exceeds_credit_limit = False
    
    def action_post(self):
        """Override post action to check credit limit for customer invoices"""
        for move in self:
            if move.move_type == 'out_invoice' and move.partner_id.credit_limit > 0:
                # Calculate total outstanding invoices
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('id', '!=', move.id if move.id else False)
                ])
                total_invoiced = sum(posted_invoices.mapped('amount_total'))
                
                # Calculate total payments received
                payments = self.env['account.payment'].search([
                    ('partner_id', '=', move.partner_id.id),
                    ('state', '=', 'posted'),
                    ('payment_type', '=', 'inbound')
                ])
                total_payments = sum(payments.mapped('amount'))
                
                # Calculate net outstanding
                net_outstanding = total_invoiced - total_payments
                total_with_current = net_outstanding + move.amount_total
                
                if total_with_current > move.partner_id.credit_limit:
                    raise UserError(
                        f"This invoice exceeds the customer's credit limit.\n"
                        f"Credit Limit: {move.partner_id.credit_limit}\n"
                        f"Current Outstanding: {net_outstanding}\n"
                        f"Current Invoice Amount: {move.amount_total}\n"
                        f"Total After Invoice: {total_with_current}\n"
                        f"Available Credit: {max(0, move.partner_id.credit_limit - net_outstanding)}\n\n"
                        f"Please contact the sales manager for override or request customer payment."
                    )
        return super(AccountMove, self).action_post()