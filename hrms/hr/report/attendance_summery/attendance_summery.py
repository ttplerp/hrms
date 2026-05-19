import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import nowdate, get_first_day, get_last_day

SHIFT_START = "09:00:00"
SHIFT_END = "17:00:00"

def execute(filters=None):
    if not filters:
        filters = {}
        
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Default current month if empty
    if not from_date:
        from_date = get_first_day(nowdate())

    if not to_date:
        to_date = get_last_day(nowdate())

    columns = get_columns()
    data = get_grouped_attendance(from_date, to_date)

    return columns, data

def get_columns():
    return [
        _("Employee ID") + ":Data:80",
        _("Employee Name") + ":Data:200",
        _("Attendance Date") + ":Date:100",
        _("In Time") + ":Time:80",
        _("Late By") + ":Data:100",        # In Time Late
        _("Early By") + ":Data:100",       # In Time Early
        _("Reason for Late Entry") + ":Data:150",  # Reason after Early By
        _("Out Time") + ":Time:80",
        _("Early Exit") + ":Data:100",     # Out Time Early
        _("Late Exit") + ":Data:100",      # Out Time Late
        _("Reason for Early Exit") + ":Data:150",  # Reason after Late Exit
        _("Status") + ":Data:100",
        _("Leave Type") + ":Data:150"
    ]


def get_grouped_attendance(from_date, to_date):
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)
    
    filters = {"docstatus": 1, "attendance_date": ["between", [from_date, to_date]]}
    
    allowed_roles = ["System Manager", "HR User"]
    if not any(role in user_roles for role in allowed_roles):
        emp = frappe.get_value("Employee", {"user_id": current_user}, "name")
        if emp:
            # ✅ Check if this employee manages others
            subordinates = frappe.get_all("Employee", filters={"reports_to": emp}, pluck="name")
            
            if subordinates:
                # Include self + subordinates
                filters["employee"] = ["in", [emp] + subordinates]
            else:
                # Only self if no one reports to them
                filters["employee"] = emp
            
    records = frappe.get_all(
        "Attendance",
        fields=[
            "employee",
            "employee_name",
            "attendance_date",
            "in_time",
            "out_time",
            "reason_for_late_entry",
            "reason_for_early_exit",
            "status",
            "leave_type"
        ],
        filters=filters,
        order_by="employee, attendance_date"
    )

    data = []
    grouped_data = {}
    for r in records:
        emp_key = (r.employee, r.employee_name)
        grouped_data.setdefault(emp_key, []).append(r)

    for (emp_id, emp_name), records in grouped_data.items():
        first_row = True
        for r in records:
            # Compute In Time Late / Early
            late_by, early_by = "00:00:00", "00:00:00"
            if r.in_time:
                shift_start_dt = datetime.combine(r.attendance_date, datetime.strptime(SHIFT_START, "%H:%M:%S").time())
                if r.in_time > shift_start_dt:
                    late_by = format_timedelta(r.in_time - shift_start_dt)
                    early_by = "00:00:00"
                elif r.in_time < shift_start_dt:
                    early_by = format_timedelta(shift_start_dt - r.in_time)
                    late_by = "00:00:00"

            # Compute Out Time Early / Late
            early_exit, late_exit = "00:00:00", "00:00:00"
            if r.out_time:
                shift_end_dt = datetime.combine(r.attendance_date, datetime.strptime(SHIFT_END, "%H:%M:%S").time())
                if r.out_time < shift_end_dt:
                    early_exit = format_timedelta(shift_end_dt - r.out_time)
                    late_exit = "00:00:00"
                elif r.out_time > shift_end_dt:
                    late_exit = format_timedelta(r.out_time - shift_end_dt)
                    early_exit = "00:00:00"
            
            # Show leave type only for On Leave / Half Day
            leave_type = ""
            if r.status in ["On Leave", "Half Day"]:
                leave_type = r.leave_type or ""

            row = [
                emp_id if first_row else "",
                emp_name if first_row else "",
                r.attendance_date,
                r.in_time.strftime("%H:%M:%S") if r.in_time else "00:00:00",
                late_by,
                early_by,
                r.reason_for_late_entry or "(blank)",
                r.out_time.strftime("%H:%M:%S") if r.out_time else "00:00:00",
                early_exit,
                late_exit,
                r.reason_for_early_exit or "(blank)",
                r.status or "",
                leave_type
            ]
            data.append(row)
            first_row = False

    return data


def format_timedelta(td):
    """Format timedelta into hh:mm:ss"""
    if not isinstance(td, timedelta):
        return "00:00:00"
    total_seconds = round(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"
