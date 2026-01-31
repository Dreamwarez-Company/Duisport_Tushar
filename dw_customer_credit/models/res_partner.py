from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    onboarding_ids = fields.One2many('res.partner.onboarding', 'partner_id', string='Onboarding History')
    active_onboarding_id = fields.Many2one('res.partner.onboarding', string='Active Onboarding', 
                                         compute='_compute_active_onboarding')
    requires_onboarding = fields.Boolean(string='Requires Onboarding', compute='_compute_requires_onboarding')
    credit_limit_reached = fields.Boolean(string='Credit Limit Reached', compute='_compute_credit_limit_reached')
    
    @api.depends('onboarding_ids', 'onboarding_ids.state')
    def _compute_active_onboarding(self):
        for partner in self:
            active_onboarding = partner.onboarding_ids.filtered(lambda o: o.state in ['draft', 'submitted', 'approved'])
            partner.active_onboarding_id = active_onboarding[0] if active_onboarding else False
    
    @api.depends('credit_limit', 'active_onboarding_id')
    def _compute_requires_onboarding(self):
        for partner in self:
            partner.requires_onboarding = not partner.active_onboarding_id and partner.customer_rank > 0
    
    @api.depends('credit_limit')
    def _compute_credit_limit_reached(self):
        for partner in self:
            if partner.credit_limit > 0 and partner.customer_rank > 0:
                # Calculate total from posted invoices
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                total_invoiced = sum(posted_invoices.mapped('amount_total'))
                
                # Calculate total payments received - IMPROVED
                payments = self.env['account.payment'].search([
                    ('partner_id', '=', partner.id),
                    ('state', '=', 'posted'),
                    ('payment_type', '=', 'inbound')
                ])
                total_payments = sum(payments.mapped('amount'))
                
                # Also check from account.move for reconciled payments
                payment_moves = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('state', '=', 'posted'),
                    ('payment_id', '!=', False)
                ])
                for move in payment_moves:
                    credit_lines = move.line_ids.filtered(
                        lambda line: line.account_id.internal_group == 'receivable' and line.credit > 0
                    )
                    total_payments += sum(credit_lines.mapped('credit'))
                
                # Calculate net outstanding
                net_outstanding = total_invoiced - total_payments
                partner.credit_limit_reached = net_outstanding >= partner.credit_limit
                
                _logger.info(
                    f"=== PARTNER CREDIT STATUS: {partner.name} ===\n"
                    f"Credit Limit: {partner.credit_limit}\n"
                    f"Total Invoiced: {total_invoiced}\n"
                    f"Total Payments: {total_payments}\n"
                    f"Net Outstanding: {net_outstanding}\n"
                    f"Credit Limit Reached: {partner.credit_limit_reached}\n"
                    f"======================================"
                )
            else:
                partner.credit_limit_reached = False
    
    def action_view_onboarding(self):
        """View onboarding history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Onboarding History',
            'res_model': 'res.partner.onboarding',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id}
        }
    
    def action_create_onboarding(self):
        """Create new onboarding form"""
        self.ensure_one()
        onboarding = self.env['res.partner.onboarding'].create({
            'partner_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner.onboarding',
            'res_id': onboarding.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.depends('credit_limit')
    def _compute_credit_limit_reached(self):
        for partner in self:
            if partner.credit_limit > 0 and partner.customer_rank > 0:
                # Calculate using residual amount
                posted_invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted')
                ])
                total_unpaid = sum(posted_invoices.mapped('amount_residual'))
                
                partner.credit_limit_reached = total_unpaid >= partner.credit_limit
                
                _logger.info(
                    f"PARTNER CREDIT STATUS - {partner.name}: "
                    f"Limit: {partner.credit_limit}, "
                    f"Unpaid: {total_unpaid}, "
                    f"Reached: {partner.credit_limit_reached}"
                )
            else:
                partner.credit_limit_reached = False