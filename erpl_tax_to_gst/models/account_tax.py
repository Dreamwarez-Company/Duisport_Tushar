# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def convert_to_gst(self, tax_ids=None, update_name=True, update_description=True):
        """
        Convert taxes to GST format
        :param tax_ids: List of tax IDs to convert. If None, convert all taxes
        :param update_name: If True, update tax names
        :param update_description: If True, update tax descriptions
        :return: Dictionary with conversion results
        """
        domain = []
        if tax_ids:
            domain = [('id', 'in', tax_ids)]
        
        taxes = self.search(domain)
        converted_count = 0
        errors = []
        
        for tax in taxes:
            try:
                vals = {}
                
                if update_name:
                    # Replace "Tax" with "GST" in name
                    if tax.name and 'tax' in tax.name.lower() and 'gst' not in tax.name.lower():
                        new_name = tax.name.replace('Tax', 'GST').replace('tax', 'GST').replace('TAX', 'GST')
                        vals['name'] = new_name
                
                if update_description:
                    # Update description if it contains tax-related terms
                    if tax.description and ('tax' in tax.description.lower() or 'vat' in tax.description.lower()):
                        new_desc = tax.description.replace('Tax', 'GST').replace('tax', 'GST').replace('TAX', 'GST')
                        new_desc = new_desc.replace('VAT', 'GST').replace('vat', 'GST').replace('Vat', 'GST')
                        vals['description'] = new_desc
                
                if vals:
                    tax.write(vals)
                    converted_count += 1
            except Exception as e:
                errors.append(f"Tax {tax.name}: {str(e)}")
        
        return {
            'converted_count': converted_count,
            'total_count': len(taxes),
            'errors': errors
        }


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    @api.model
    def convert_to_gst(self, group_ids=None, update_name=True):
        """
        Convert tax groups to GST format
        :param group_ids: List of group IDs to convert. If None, convert all groups
        :param update_name: If True, update group names
        :return: Dictionary with conversion results
        """
        domain = []
        if group_ids:
            domain = [('id', 'in', group_ids)]
        
        groups = self.search(domain)
        converted_count = 0
        errors = []
        
        for group in groups:
            try:
                if update_name:
                    # Replace "Tax" with "GST" in name
                    if group.name and 'tax' in group.name.lower() and 'gst' not in group.name.lower():
                        new_name = group.name.replace('Tax', 'GST').replace('tax', 'GST').replace('TAX', 'GST')
                        group.write({'name': new_name})
                        converted_count += 1
            except Exception as e:
                errors.append(f"Tax Group {group.name}: {str(e)}")
        
        return {
            'converted_count': converted_count,
            'total_count': len(groups),
            'errors': errors
        }

