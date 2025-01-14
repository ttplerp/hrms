import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class MREmployeeAttendanceTool(Document):
    pass


@frappe.whitelist()
def get_mr_employees(date, branch=None, muster_roll_group=None, company=None):
    if not branch:
        frappe.throw(_("Please select a branch"))
    if not muster_roll_group:
        frappe.throw(_("Please select a muster roll group"))
    if not date:
        frappe.throw(_("Please select a date"))
    if not company:
        frappe.throw(_("Please select a company"))

    attendance_not_marked = []
    attendance_marked = []

    # Filters for query
    filters = frappe._dict(
        date=date,
        company=company,
        branch=branch,
        muster_roll_group=muster_roll_group,
    )

    # Fetch muster roll employees
    mr_employee_list = get_mr_employee_list(filters=filters, as_dict=True)
    if not mr_employee_list:
        error_msg = _(
            "No muster roll employees found for the mentioned criteria:<br>"
            "Branch: {0}, Muster Roll Group: {1}"
        ).format(frappe.bold(branch), frappe.bold(muster_roll_group))
        frappe.throw(error_msg, title=_("No MR Employees Found"))

    # Fetch attendance for the given date
    marked_employee = {
        emp["mr_employee"]: emp["status"]
        for emp in frappe.get_list(
            "Muster Roll Attendance",
            fields=["mr_employee", "status"],
            filters={"date": date, "docstatus": 1},
        )
    }

    # Separate marked and unmarked employees
    for mr_employee in mr_employee_list:
        mr_employee["status"] = marked_employee.get(mr_employee["mr_employee"])
        if mr_employee["mr_employee"] not in marked_employee:
            attendance_not_marked.append(mr_employee)
        else:
            attendance_marked.append(mr_employee)

    return {"marked": attendance_marked, "unmarked": attendance_not_marked}


def get_mr_employee_list(filters, as_dict=True) -> list:
    """Fetch muster roll employees filtered by active status and other criteria."""
    MREmployee = frappe.qb.DocType("Muster Roll Employee")
    query = (
        frappe.qb.from_(MREmployee)
        .where(
            (MREmployee.status == "Active")
            & (MREmployee.company == filters.company)
            & (MREmployee.branch == filters.branch)
            & (MREmployee.muster_roll_group == filters.muster_roll_group)
        )
        .select(
            MREmployee.name.as_("mr_employee"),
            MREmployee.person_name.as_("mr_employee_name"),
        )
    )
    return query.run(as_dict=as_dict)


@frappe.whitelist()
def mark_mr_employee_attendance(mr_employee_list, status, date, company=None):
    """Mark attendance for multiple muster roll employees."""
    mr_employee_list = json.loads(mr_employee_list)

    if not mr_employee_list:
        frappe.throw(_("Employee list cannot be empty"))

    # Prepare attendance documents
    attendance_docs = []
    for mr_employee in mr_employee_list:
        employee_company = frappe.db.get_value(
            "Muster Roll Employee", mr_employee["mr_employee"], "company", cache=True
        )
        attendance_docs.append(
            {
                "doctype": "Muster Roll Attendance",
                "mr_employee": mr_employee.get("mr_employee"),
                "employee_name": mr_employee.get("mr_employee_name"),
                "date": getdate(date),
                "status": status,
                "company": employee_company or company,
            }
        )

    # Bulk insert and submit
    attendance_records = [frappe.get_doc(doc) for doc in attendance_docs]
    for attendance in attendance_records:
        attendance.insert()
        attendance.submit()

    return {"message": _("Attendance marked successfully"), "count": len(attendance_docs)}
