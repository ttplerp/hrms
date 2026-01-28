# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WorkforceRequisition(Document):
	pass

@frappe.whitelist()
def get_workforce_requisiton_approver(user_id):
    # Step 1: Get username from User doctype
    username = frappe.db.get_value("User", user_id, "username")
    if not username:
        return None

    # Step 2: Find Employee linked to the requesting user (requested_by)
    employee_id = frappe.db.get_value("Employee", {"name": username}, "name")
    if not employee_id:
        return None

    # Step 3: Fetch the expense approver (this stores USER ID, not EMPLOYEE ID)
    approver_user = frappe.db.get_value("Employee", employee_id, "expense_approver")
    approver_name = frappe.db.get_value("Employee", employee_id, "expense_approver_name")

    if not approver_user:
        return None

    # Step 4: Get the APPROVER EMPLOYEE ID using the approver user
    approver_username = frappe.db.get_value("User", approver_user, "username")
    approver_employee_id = frappe.db.get_value("Employee", {"name": approver_username}, "name")

    # Step 5: Now fetch the designation from approver employee record
    approver_designation = frappe.db.get_value("Employee", approver_employee_id, "designation")

    return {
        "approver": approver_user,
        "approver_name": approver_name,
        "approver_designation": approver_designation
    }
