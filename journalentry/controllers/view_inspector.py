from odoo import http
from odoo.http import request
import json

class ViewInspectorController(http.Controller):
    
    @http.route('/journalentry/inspect_view/<string:xml_id>', type='http', auth='user')
    def inspect_view(self, xml_id, **kwargs):
        """Inspect a view by its XML ID"""
        try:
            view = request.env.ref(xml_id)
            view_data = {
                'id': view.id,
                'name': view.name,
                'model': view.model,
                'type': view.type,
                'arch': view.arch,
                'inherit_id': view.inherit_id.id if view.inherit_id else None,
                'inherit_id_name': view.inherit_id.name if view.inherit_id else None,
            }
            
            # Get all fields in the view
            fields = []
            for field in view.arch.split('<field'):
                if 'name="' in field:
                    field_name = field.split('name="')[1].split('"')[0]
                    fields.append(field_name)
            
            view_data['fields'] = sorted(list(set(fields)))
            
            # Get all pages/tabs
            pages = []
            for page in view.arch.split('<page'):
                if 'name="' in page:
                    page_name = page.split('name="')[1].split('"')[0]
                    pages.append(page_name)
            
            view_data['pages'] = sorted(list(set(pages)))
            
            return request.make_response(
                json.dumps(view_data, indent=2),
                headers=[('Content-Type', 'application/json')]
            )
        except Exception as e:
            return request.make_response(
                json.dumps({'error': str(e)}, indent=2),
                headers=[('Content-Type', 'application/json')]
            )
    
    @http.route('/journalentry/inspect_account_move_form', type='http', auth='user')
    def inspect_account_move_form(self, **kwargs):
        """Specifically inspect the account.move form view"""
        return self.inspect_view('account.view_move_form')