from odoo import http
from odoo.http import request

class ModelFieldsController(http.Controller):

    @http.route('/fields/<string:model>', type='http', auth='user')
    def list_fields(self, model):
        try:
            model_obj = request.env[model]

            fields_data = model_obj.fields_get()

            html = f"<h1>Fields for model: {model}</h1>"
            html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
            html += "<tr><th>Name</th><th>Type</th><th>String</th><th>Sample Value</th></tr>"

            record = model_obj.search([], limit=1)

            for field_name, field_info in fields_data.items():
                field_type = field_info.get("type")
                field_string = field_info.get("string")

                # get sample value
                if record:
                    try:
                        value = getattr(record, field_name)
                    except:
                        value = "N/A"
                else:
                    value = "No Records"

                html += f"""
                    <tr>
                        <td>{field_name}</td>
                        <td>{field_type}</td>
                        <td>{field_string}</td>
                        <td>{value}</td>
                    </tr>
                """

            html += "</table>"
            return html

        except Exception as e:
            return f"<h3>Error:</h3><pre>{str(e)}</pre>"
