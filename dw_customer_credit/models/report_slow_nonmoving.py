# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import date, datetime, timedelta
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)

class ReportSlowNonMoving(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_slow_nonmoving_template'
    _description = 'Slow / Non-Moving Inventory Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['slow.moving.wizard'].browse(docids)
        slow_days = int(wizard.slow_days or 0)
        non_moving_days = int(wizard.non_moving_days or 0)
        today = fields.Date.context_today(self)

        domain = [
            ('detailed_type', '=', 'product'),
            ('qty_available', '>', 0)
        ]
        
        if wizard.product_category_id:
            domain.append(('categ_id', 'child_of', wizard.product_category_id.id))
        
        if wizard.product_id:
            domain.append(('id', '=', wizard.product_id.id))
        
        products = self.env['product.product'].search(domain)
        
        lines = []
        total_summary = {
            'total_qty': 0.0,
            'total_value': 0.0,
            'total_lots': 0,
            'slow_moving_count': 0,
            'non_moving_count': 0,
            'active_count': 0
        }

        for product in products:
            lots = self.env['stock.lot'].search([
                ('product_id', '=', product.id),
                ('company_id', '=', self.env.company.id),
            ])
            
            if not lots:
                continue
            
            lot_info = []
            total_qty = 0
            total_value = 0
            oldest_lot_info = None
            newest_lot_info = None
            oldest_date = None
            newest_date = None
            
            for lot in lots:
                # Get remaining quantity
                if wizard.location_id:
                    quant = self.env['stock.quant'].search([
                        ('lot_id', '=', lot.id),
                        ('location_id', 'child_of', wizard.location_id.id),
                        ('quantity', '>', 0)
                    ], limit=1)
                else:
                    quant = self.env['stock.quant'].search([
                        ('lot_id', '=', lot.id),
                        ('quantity', '>', 0)
                    ], limit=1)
                
                remaining_qty = quant.quantity if quant else 0.0
                
                if remaining_qty <= 0:
                    continue
                
                # Find first incoming move (original receipt)
                first_incoming = self.env['stock.move.line'].search([
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'internal'),
                    ('quantity', '>', 0)
                ], order='date asc', limit=1)
                
                original_qty = first_incoming.quantity if first_incoming else remaining_qty
                
                used_qty = original_qty - remaining_qty
                used_qty = max(used_qty, 0.0)
                
                # Lot date (receipt date)
                lot_datetime = first_incoming.date if first_incoming else lot.create_date or datetime.now()
                lot_date = lot_datetime.date()
                days_in_stock = (today - lot_date).days
                days_in_stock = max(days_in_stock, 0)
                
                cost = product.standard_price or 0.0
                lot_value = remaining_qty * cost
                
                reference = ''
                if first_incoming and first_incoming.picking_id:
                    if first_incoming.picking_id.origin:
                        reference = f"{first_incoming.picking_id.name} ({first_incoming.picking_id.origin})"
                    else:
                        reference = first_incoming.picking_id.name
                
                lot_data = {
                    'lot_name': lot.name,
                    'lot_id': lot.id,
                    'date': lot_date,
                    'datetime': lot_datetime,
                    'remaining_qty': remaining_qty,
                    'original_qty': original_qty,
                    'used_qty': used_qty,
                    'days': days_in_stock,
                    'value': lot_value,
                    'reference': reference or lot.name,
                }
                lot_info.append(lot_data)
                
                total_qty += remaining_qty
                total_value += lot_value
                
                # Track oldest and newest
                if not oldest_lot_info or lot_datetime < oldest_lot_info['datetime']:
                    oldest_lot_info = lot_data
                    oldest_date = lot_date
                
                if not newest_lot_info or lot_datetime > newest_lot_info['datetime']:
                    newest_lot_info = lot_data
                    newest_date = lot_date
            
            if total_qty <= 0 or not lot_info:
                continue
            
            oldest_days = (today - oldest_date).days if oldest_date else 0
            
            if oldest_days >= non_moving_days:
                classification = 'Non-Moving'
                total_summary['non_moving_count'] += 1
            elif oldest_days >= slow_days:
                classification = 'Slow Moving'
                total_summary['slow_moving_count'] += 1
            else:
                classification = 'Active'
                total_summary['active_count'] += 1
            
            # Age buckets with used/remaining info
            age_buckets = {
                '0-15 Days': {'qty': 0, 'value': 0, 'lots': []},
                '16-30 Days': {'qty': 0, 'value': 0, 'lots': []},
                '31-60 Days': {'qty': 0, 'value': 0, 'lots': []},
                '61-120 Days': {'qty': 0, 'value': 0, 'lots': []},
                '121-180 Days': {'qty': 0, 'value': 0, 'lots': []},
                '180+ Days': {'qty': 0, 'value': 0, 'lots': []},
            }
            
            for info in lot_info:
                days = info['days']
                bucket = '180+ Days'
                if days <= 15:
                    bucket = '0-15 Days'
                elif days <= 30:
                    bucket = '16-30 Days'
                elif days <= 60:
                    bucket = '31-60 Days'
                elif days <= 120:
                    bucket = '61-120 Days'
                elif days <= 180:
                    bucket = '121-180 Days'
                
                age_buckets[bucket]['qty'] += info['remaining_qty']
                age_buckets[bucket]['value'] += info['value']
                age_buckets[bucket]['lots'].append({
                    'name': info['lot_name'],
                    'remaining_qty': info['remaining_qty'],
                    'used_qty': info['used_qty'],
                    'original_qty': info['original_qty'],
                    'days': info['days'],
                    'reference': info['reference']
                })
            
            total_summary['total_qty'] += total_qty
            total_summary['total_value'] += total_value
            total_summary['total_lots'] += len(lot_info)
            
            lot_names = [info['lot_name'] for info in lot_info[:5]]
            if len(lot_info) > 5:
                lot_names.append(f"... and {len(lot_info) - 5} more lots")
            
            lines.append({
                'product': product.display_name,
                'code': product.default_code or '',
                'category': product.categ_id.display_name or 'All',
                'total_qty': total_qty,
                'total_value': total_value,
                'oldest_date': oldest_date,
                'oldest_days': oldest_days,
                'oldest_lot': oldest_lot_info['lot_name'] if oldest_lot_info else '',
                'oldest_reference': oldest_lot_info['reference'] if oldest_lot_info else '',
                'newest_date': newest_date,
                'newest_days': (today - newest_date).days if newest_date else 0,
                'newest_lot': newest_lot_info['lot_name'] if newest_lot_info else '',
                'newest_reference': newest_lot_info['reference'] if newest_lot_info else '',
                'classification': classification,
                'lot_count': len(lot_info),
                'lot_names': lot_names,
                'all_lots_count': len(lot_info),
                'age_buckets': age_buckets,
                'lot_info': lot_info,
            })

        lines.sort(key=lambda x: (
            x['classification'] != 'Non-Moving',
            x['classification'] != 'Slow Moving',
            -x['oldest_days']
        ))

        all_age_buckets = {
            '0-15 Days': {'qty': 0, 'value': 0},
            '16-30 Days': {'qty': 0, 'value': 0},
            '31-60 Days': {'qty': 0, 'value': 0},
            '61-120 Days': {'qty': 0, 'value': 0},
            '121-180 Days': {'qty': 0, 'value': 0},
            '180+ Days': {'qty': 0, 'value': 0},
        }
        
        for line in lines:
            for bucket_name, bucket_data in line['age_buckets'].items():
                if bucket_name in all_age_buckets:
                    all_age_buckets[bucket_name]['qty'] += bucket_data['qty']
                    all_age_buckets[bucket_name]['value'] += bucket_data['value']

        return {
            'docs': wizard,
            'lines': lines,
            'today': today.strftime('%d/%m/%Y'),
            'slow_days': slow_days,
            'non_moving_days': non_moving_days,
            'total_summary': total_summary,
            'all_age_buckets': all_age_buckets,
            'location_info': wizard.location_id.display_name if wizard.location_id else None,
            'product_category': wizard.product_category_id.display_name if wizard.product_category_id else 'All',
            'show_age_buckets': wizard.show_age_buckets,
            'thresholds': {
                '15': wizard.threshold_15_days,
                '30': wizard.threshold_30_days,
                '60': wizard.threshold_60_days,
                '120': wizard.threshold_120_days,
                '180': wizard.threshold_180_days,
            }
        }


# # -*- coding: utf-8 -*-
# from odoo import api, models, fields
# from datetime import date, datetime, timedelta
# from collections import defaultdict
# import logging

# _logger = logging.getLogger(__name__)

# class ReportSlowNonMoving(models.AbstractModel):
#     _name = 'report.dw_customer_credit.report_slow_nonmoving_template'
#     _description = 'Slow / Non-Moving Inventory Report'

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         wizard = self.env['slow.moving.wizard'].browse(docids)
#         slow_days = int(wizard.slow_days or 0)
#         non_moving_days = int(wizard.non_moving_days or 0)
#         today = fields.Date.context_today(self)

#         # Build domain for products
#         domain = [
#             ('detailed_type', '=', 'product'),
#             ('qty_available', '>', 0)
#         ]
        
#         if wizard.product_category_id:
#             domain.append(('categ_id', 'child_of', wizard.product_category_id.id))
        
#         if wizard.product_id:
#             domain.append(('id', '=', wizard.product_id.id))
        
#         products = self.env['product.product'].search(domain)
        
#         lines = []
#         total_summary = {
#             'total_qty': 0.0,
#             'total_value': 0.0,
#             'total_lots': 0,
#             'slow_moving_count': 0,
#             'non_moving_count': 0,
#             'active_count': 0
#         }

#         for product in products:
#             # Get all lots for this product
#             lots = self.env['stock.lot'].search([
#                 ('product_id', '=', product.id),
#                 ('company_id', '=', self.env.company.id),
#             ])
            
#             if not lots:
#                 continue
            
#             # Filter lots that have available quantity
#             lot_info = []
#             total_qty = 0
#             total_value = 0
#             oldest_date = None
#             newest_date = None
#             oldest_lot_info = None
#             newest_lot_info = None
            
#             for lot in lots:
#                 # Get quantity in specified location
#                 if wizard.location_id:
#                     quant = self.env['stock.quant'].search([
#                         ('lot_id', '=', lot.id),
#                         ('location_id', 'child_of', wizard.location_id.id),
#                         ('quantity', '>', 0)
#                     ], limit=1)
#                 else:
#                     quant = self.env['stock.quant'].search([
#                         ('lot_id', '=', lot.id),
#                         ('quantity', '>', 0)
#                     ], limit=1)
                
#                 if not quant or quant.quantity <= 0:
#                     continue
                
#                 # Get lot creation date or first receipt date
#                 lot_datetime = lot.create_date if lot.create_date else datetime.now()
                
#                 # Try to find the first receipt move for this lot
#                 first_move = self.env['stock.move.line'].search([
#                     ('lot_id', '=', lot.id),
#                     ('state', '=', 'done'),
#                     ('location_dest_id.usage', '=', 'internal'),
#                     ('quantity', '>', 0)
#                 ], order='date asc', limit=1)
                
#                 if first_move and first_move.date:
#                     lot_datetime = first_move.date
                
#                 lot_date = lot_datetime.date()
#                 days_in_stock = (today - lot_date).days
#                 days_in_stock = max(days_in_stock, 0)
                
#                 # Calculate cost
#                 cost = product.standard_price or 0.0
#                 lot_value = quant.quantity * cost
                
#                 # Get reference information
#                 reference = ''
#                 if first_move and first_move.picking_id:
#                     if first_move.picking_id.origin:
#                         reference = f"{first_move.picking_id.name} ({first_move.picking_id.origin})"
#                     else:
#                         reference = first_move.picking_id.name
                
#                 lot_data = {
#                     'lot_name': lot.name,
#                     'lot_id': lot.id,
#                     'date': lot_date,
#                     'datetime': lot_datetime,
#                     'qty': quant.quantity,
#                     'days': days_in_stock,
#                     'value': lot_value,
#                     'reference': reference or lot.name,
#                 }
#                 lot_info.append(lot_data)
                
#                 total_qty += quant.quantity
#                 total_value += lot_value
                
#                 # Track oldest and newest lots based on receipt datetime
#                 if not oldest_lot_info or lot_datetime < oldest_lot_info['datetime']:
#                     oldest_lot_info = lot_data
#                     oldest_date = lot_date
                
#                 if not newest_lot_info or lot_datetime > newest_lot_info['datetime']:
#                     newest_lot_info = lot_data
#                     newest_date = lot_date
            
#             if total_qty <= 0 or not lot_info:
#                 continue
            
#             # Calculate oldest days
#             oldest_days = (today - oldest_date).days if oldest_date else 0
            
#             # Classify based on oldest lot
#             if oldest_days >= non_moving_days:
#                 classification = 'Non-Moving'
#                 total_summary['non_moving_count'] += 1
#             elif oldest_days >= slow_days:
#                 classification = 'Slow Moving'
#                 total_summary['slow_moving_count'] += 1
#             else:
#                 classification = 'Active'
#                 total_summary['active_count'] += 1
            
#             # Group by age buckets
#             age_buckets = {
#                 '0-15 Days': {'qty': 0, 'value': 0, 'lots': []},
#                 '16-30 Days': {'qty': 0, 'value': 0, 'lots': []},
#                 '31-60 Days': {'qty': 0, 'value': 0, 'lots': []},
#                 '61-120 Days': {'qty': 0, 'value': 0, 'lots': []},
#                 '121-180 Days': {'qty': 0, 'value': 0, 'lots': []},
#                 '180+ Days': {'qty': 0, 'value': 0, 'lots': []},
#             }
            
#             for info in lot_info:
#                 days = info['days']
#                 if days <= 15:
#                     bucket = '0-15 Days'
#                 elif days <= 30:
#                     bucket = '16-30 Days'
#                 elif days <= 60:
#                     bucket = '31-60 Days'
#                 elif days <= 120:
#                     bucket = '61-120 Days'
#                 elif days <= 180:
#                     bucket = '121-180 Days'
#                 else:
#                     bucket = '180+ Days'
                
#                 age_buckets[bucket]['qty'] += info['qty']
#                 age_buckets[bucket]['value'] += info['value']
#                 age_buckets[bucket]['lots'].append({
#                     'name': info['lot_name'],
#                     'qty': info['qty'],
#                     'days': info['days'],
#                     'reference': info['reference']
#                 })
            
#             # Update totals
#             total_summary['total_qty'] += total_qty
#             total_summary['total_value'] += total_value
#             total_summary['total_lots'] += len(lot_info)
            
#             # Prepare lot names for display
#             lot_names = [info['lot_name'] for info in lot_info[:5]]
#             if len(lot_info) > 5:
#                 lot_names.append(f"... and {len(lot_info) - 5} more lots")
            
#             lines.append({
#                 'product': product.display_name,
#                 'code': product.default_code or '',
#                 'category': product.categ_id.display_name or 'All',
#                 'total_qty': total_qty,
#                 'total_value': total_value,
#                 'oldest_date': oldest_date,
#                 'oldest_days': oldest_days,
#                 'oldest_lot': oldest_lot_info['lot_name'] if oldest_lot_info else '',
#                 'oldest_reference': oldest_lot_info['reference'] if oldest_lot_info else '',
#                 'newest_date': newest_date,
#                 'newest_days': (today - newest_date).days if newest_date else 0,
#                 'newest_lot': newest_lot_info['lot_name'] if newest_lot_info else '',
#                 'newest_reference': newest_lot_info['reference'] if newest_lot_info else '',
#                 'classification': classification,
#                 'lot_count': len(lot_info),
#                 'lot_names': lot_names,
#                 'all_lots_count': len(lot_info),
#                 'age_buckets': age_buckets,
#                 'lot_info': lot_info,
#             })

#         # Sort: Non-Moving first, then Slow Moving, then by days descending
#         lines.sort(key=lambda x: (
#             x['classification'] != 'Non-Moving',
#             x['classification'] != 'Slow Moving',
#             -x['oldest_days']
#         ))

#         # Calculate overall age buckets
#         all_age_buckets = {
#             '0-15 Days': {'qty': 0, 'value': 0},
#             '16-30 Days': {'qty': 0, 'value': 0},
#             '31-60 Days': {'qty': 0, 'value': 0},
#             '61-120 Days': {'qty': 0, 'value': 0},
#             '121-180 Days': {'qty': 0, 'value': 0},
#             '180+ Days': {'qty': 0, 'value': 0},
#         }
        
#         for line in lines:
#             for bucket_name, bucket_data in line['age_buckets'].items():
#                 if bucket_name in all_age_buckets:
#                     all_age_buckets[bucket_name]['qty'] += bucket_data['qty']
#                     all_age_buckets[bucket_name]['value'] += bucket_data['value']

#         return {
#             'docs': wizard,
#             'lines': lines,
#             'today': today.strftime('%d/%m/%Y'),
#             'slow_days': slow_days,
#             'non_moving_days': non_moving_days,
#             'total_summary': total_summary,
#             'all_age_buckets': all_age_buckets,
#             'location_info': wizard.location_id.display_name if wizard.location_id else None,
#             'product_category': wizard.product_category_id.display_name if wizard.product_category_id else 'All',
#             'show_age_buckets': wizard.show_age_buckets,
#             'thresholds': {
#                 '15': wizard.threshold_15_days,
#                 '30': wizard.threshold_30_days,
#                 '60': wizard.threshold_60_days,
#                 '120': wizard.threshold_120_days,
#                 '180': wizard.threshold_180_days,
#             }
#         }



