# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TaxToGstWizard(models.TransientModel):
    _name = 'erpl.tax.to.gst.wizard'
    _description = 'Tax to GST Conversion Wizard'

    conversion_type = fields.Selection([
        ('all', 'Convert All Taxes'),
        ('selected', 'Convert Selected Taxes'),
    ], string='Conversion Type', default='all', required=True)
    
    tax_ids = fields.Many2many('account.tax', string='Select Taxes',
                               domain=[], help='Select specific taxes to convert')
    
    tax_group_ids = fields.Many2many('account.tax.group', string='Select Tax Groups',
                                     domain=[], help='Select specific tax groups to convert')
    
    update_tax_name = fields.Boolean(string='Update Tax Names', default=True,
                                    help='Replace "Tax" with "GST" in tax names')
    
    update_tax_description = fields.Boolean(string='Update Tax Descriptions', default=True,
                                           help='Replace "Tax" with "GST" in tax descriptions')
    
    update_tax_group_name = fields.Boolean(string='Update Tax Group Names', default=True,
                                          help='Replace "Tax" with "GST" in tax group names')
    
    convert_tax_groups = fields.Boolean(string='Convert Tax Groups', default=True,
                                       help='Also convert tax groups to GST format')
    
    preview_mode = fields.Boolean(string='Preview Mode', default=False,
                                  help='Preview changes without applying them')
    
    result_message = fields.Text(string='Result', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(TaxToGstWizard, self).default_get(fields_list)
        return res

    def action_preview(self):
        """Preview the changes that will be made"""
        self.ensure_one()
        self.preview_mode = True
        return self.action_convert()

    def action_convert(self):
        """Execute the conversion"""
        self.ensure_one()
        
        if not self.update_tax_name and not self.update_tax_description and not self.update_tax_group_name:
            raise UserError(_('Please select at least one option to update (Tax Names, Descriptions, or Tax Group Names).'))
        
        result_messages = []
        total_converted = 0
        total_errors = 0
        
        # Convert taxes
        if self.update_tax_name or self.update_tax_description:
            tax_ids = None
            if self.conversion_type == 'selected' and self.tax_ids:
                tax_ids = self.tax_ids.ids
            
            tax_model = self.env['account.tax']
            result = tax_model.convert_to_gst(
                tax_ids=tax_ids,
                update_name=self.update_tax_name,
                update_description=self.update_tax_description
            )
            
            if result['converted_count'] > 0:
                result_messages.append(_('Taxes: %s converted out of %s') % (result['converted_count'], result['total_count']))
                total_converted += result['converted_count']
            
            if result['errors']:
                result_messages.append(_('Tax Errors: %s') % len(result['errors']))
                total_errors += len(result['errors'])
                for error in result['errors'][:5]:  # Show first 5 errors
                    result_messages.append(f"  - {error}")
                if len(result['errors']) > 5:
                    result_messages.append(_('  ... and %s more errors') % (len(result['errors']) - 5))
        
        # Convert tax groups
        if self.convert_tax_groups and self.update_tax_group_name:
            group_ids = None
            if self.conversion_type == 'selected' and self.tax_group_ids:
                group_ids = self.tax_group_ids.ids
            
            group_model = self.env['account.tax.group']
            result = group_model.convert_to_gst(
                group_ids=group_ids,
                update_name=self.update_tax_group_name
            )
            
            if result['converted_count'] > 0:
                result_messages.append(_('Tax Groups: %s converted out of %s') % (result['converted_count'], result['total_count']))
                total_converted += result['converted_count']
            
            if result['errors']:
                result_messages.append(_('Tax Group Errors: %s') % len(result['errors']))
                total_errors += len(result['errors'])
                for error in result['errors'][:5]:  # Show first 5 errors
                    result_messages.append(f"  - {error}")
                if len(result['errors']) > 5:
                    result_messages.append(_('  ... and %s more errors') % (len(result['errors']) - 5))
        
        # Prepare final message
        if self.preview_mode:
            message = _('PREVIEW MODE - No changes were applied.\n\n')
        else:
            message = _('Conversion completed!\n\n')
        
        message += _('Total Converted: %s\n') % total_converted
        message += _('Total Errors: %s\n\n') % total_errors
        
        if result_messages:
            message += '\n'.join(result_messages)
        else:
            message += _('No changes were made. Please check your selection criteria.')
        
        self.result_message = message
        
        if self.preview_mode:
            # Return to form view to show preview
            return {
                'type': 'ir.actions.act_window',
                'name': _('Preview Conversion'),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context,
            }
        else:
            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Conversion Complete'),
                    'message': message,
                    'type': 'success' if total_errors == 0 else 'warning',
                    'sticky': True,
                }
            }

