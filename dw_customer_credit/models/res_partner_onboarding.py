from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ResPartnerOnboarding(models.Model):
    _name = 'res.partner.onboarding'
    _description = 'Customer Onboarding Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('customer_rank', '>', 0)])
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # Credit Information
    
    credit_limit = fields.Float(string='Credit Limit', required=True, tracking=True)
    # credit_days = fields.Integer(string='Credit Days', required=True, tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', required=True)
    
    # Onboarding Details
    onboarding_date = fields.Date(string='Onboarding Date', default=fields.Date.today)
    onboarding_team_id = fields.Many2one('res.users', string='Onboarding Team', default=lambda self: self.env.user)
    reason_for_onboarding = fields.Text(string='Business Reason')
    risk_assessment = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk')
    ], string='Risk Assessment', default='medium')
    
    # Approval Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active')
    ], string='Status', default='draft', tracking=True)
    
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Constraints
    _sql_constraints = [
        ('unique_partner_draft', 'unique(partner_id, state)', 'A customer can only have one draft onboarding form at a time.'),
    ]
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('res.partner.onboarding') or 'New'
        return super(ResPartnerOnboarding, self).create(vals)
    
    @api.constrains('credit_limit')
    def _check_credit_limit(self):
        for record in self:
            if record.credit_limit < 0:
                raise ValidationError("Credit limit cannot be negative.")
    
    @api.constrains('credit_days')
    def _check_credit_days(self):
        for record in self:
            if record.credit_days < 0:
                raise ValidationError("Credit days cannot be negative.")
            if record.credit_days > 365:
                raise ValidationError("Credit days cannot exceed 365 days.")
    
    def action_submit(self):
        """Submit onboarding form for approval"""
        self.write({'state': 'submitted'})
        # Notify managers for approval
        self._notify_managers()
    
    # def action_approve(self):
    #     """Approve the onboarding form"""
    #     if not self.env.user.has_group('sales_team.group_sale_manager'):
    #         raise UserError("Only Sales Managers can approve onboarding forms.")
        
    #     # Update partner with approved credit terms - CORRECTED FIELD NAME
    #     self.partner_id.write({
    #         'credit_limit': self.credit_limit,
    #         'property_payment_term_id': self.payment_term_id.id,  # CORRECTED: property_payment_term_id
    #     })
        
    #     self.write({
    #         'state': 'approved',
    #         'approved_by': self.env.user.id,
    #         'approved_date': fields.Datetime.now(),
    #     })
        
    #     # Activate the customer
    #     self.action_activate()
    
    # def action_reject(self):
    #     """Reject the onboarding form"""
    #     if not self.env.user.has_group('sales_team.group_sale_manager'):
    #         raise UserError("Only Sales Managers can reject onboarding forms.")
        
    #     # For now, just reject without wizard - you can enhance later
    #     self.write({
    #         'state': 'rejected',
    #         'rejection_reason': 'Rejected by manager'
    #     })
    
    def action_approve(self):
        """Approve the onboarding form"""
        # Allow both Sales Managers and Customer Approvers
        if not (
            self.env.user.has_group('sales_team.group_sale_manager')
            or self.env.user.has_group('dw_customer_credit.group_res_partner_onboarding_approver')
        ):
            raise UserError("Only Customer Approvers or Sales Managers can approve onboarding forms.")

        # Write partner info with elevated rights (sudo)
        self.partner_id.sudo().write({
            'credit_limit': self.credit_limit,
            'property_payment_term_id': self.payment_term_id.id,
        })

        # Update onboarding record
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })

        # Activate the customer
        self.action_activate()



    def action_reject(self):
        """Reject the onboarding form"""
        # Allow both Sales Managers and Customer Approvers
        if not (
            self.env.user.has_group('sales_team.group_sale_manager')
            or self.env.user.has_group('dw_customer_credit.group_res_partner_onboarding_approver')
        ):
            raise UserError("Only Customer Approvers.")
        
        self.write({
            'state': 'rejected',
            'rejection_reason': 'Rejected by approver',
        })




    # def action_activate(self):
    #     """Activate the customer after approval"""
    #     self.partner_id.write({
    #         'active': True,
    #         'credit_limit': self.credit_limit,
    #         'property_payment_term_id': self.payment_term_id.id,  # CORRECTED: property_payment_term_id
    #     })
    #     self.write({'state': 'active'})

    def action_activate(self):
        """Activate the customer after approval"""
        self.partner_id.sudo().write({
            'active': True,
            'credit_limit': self.credit_limit,
            'property_payment_term_id': self.payment_term_id.id,
        })
        self.write({'state': 'active'})

    
    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
    
    def _notify_managers(self):
        """Notify sales managers about pending approval"""
        manager_group = self.env.ref('sales_team.group_sale_manager')
        managers = manager_group.users
        
        for manager in managers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                note=f'Customer onboarding form for {self.partner_id.name} needs approval.',
                user_id=manager.id
            )