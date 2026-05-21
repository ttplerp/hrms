import frappe
import json
from frappe.model.document import Document
from werkzeug.wrappers import Response
from hrms.auth import token_auth_required
from frappe import _

@frappe.whitelist()
def get_all():
	data = frappe.db.sql("select name as id,full_name,age,work_address from `tabFrappe Training`", as_dict=1)
	return data
	# return {"message":"success", "data": data}

@frappe.whitelist(methods=['GET'])
def get_by_id(id):
	data = frappe.db.sql("select name as id,full_name,age,work_address from `tabFrappe Training` where name=%s", id, as_dict=1)
	return data
	# return {"message":"successful", "data": data}

@frappe.whitelist(methods=['POST'])
def create_trainee_list():
	data = json.loads(frappe.request.data)
	
	try:
		if not data.get("name"):
			raise ValueError('Invalid name value')
		doc = frappe.new_doc("Frappe Training")
		doc.full_name = data.get("name")
		doc.age = data.get("age")
		doc.work_address = data.get("address")
		doc.insert()
		return {'status_code':200,  'message': 'created success'}
	except Exception as e:
		return {'status_code':502,  'message': 'Server error'}

@frappe.whitelist(allow_guest=False)
@token_auth_required
def get_secure_data():
    """Example protected API method"""
    return {
        "message": _("Authenticated successfully"),
        "user": frappe.session.user
    }