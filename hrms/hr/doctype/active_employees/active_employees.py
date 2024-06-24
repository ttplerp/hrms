# File: your_app/hr/doctype/active_employees/active_employees.py

import frappe
from frappe.utils import now_datetime, add_to_date
from frappe import _

def fetch_active_employee():
    try:
        # Get activity logs for the current day
        activities = frappe.get_all("Activity Log",
                                    filters={"creation": (">", add_to_date(now_datetime(), days=-1)),
                                             "status": "Success"},
                                    fields=["user", "method", "reference_doctype", "reference_name", "creation"])

        for activity in activities:
            # Check if the user is linked to an Employee record
            employee = frappe.get_value("Employee", {"user_id": activity.user}, "name")
            if employee:
                # Create or update record in Active Employees doctype
                active_employee = frappe.new_doc("Active Employees")
                active_employee.employee = employee
                active_employee.activity_method = activity.method
                active_employee.reference_doctype = activity.reference_doctype
                active_employee.reference_name = activity.reference_name
                active_employee.activity_time = activity.creation
                active_employee.insert(ignore_permissions=True)

        frappe.db.commit()
        frappe.log_success(_("Active employees fetched successfully."))
    except Exception as e:
        frappe.log_error(_("Error fetching active employees: {0}").format(e))
        frappe.db.rollback()
@frappe.whitelist()
def fetch_employee_activities():
    pass
