# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe import _


def get_dashboard_for_employee(data):
	return {
		"heatmap": True,
		"heatmap_message": _("This is based on the attendance of this Employee"),
		"fieldname": "employee",
		"non_standard_fieldnames": {"Bank Account": "party", "Employee Grievance": "raised_by"},
		"method": "hrms.overrides.employee_master.get_timeline_data",
		"transactions": [
			{"label": _("Attendance"), "items": ["Attendance", "Attendance Request", "Employee Checkin"]},
			{
				"label": _("Leave"),
				"items": ["Leave Application", "Leave Allocation", "Leave Policy Assignment"],
			},
			{
				"label": _("Lifecycle"),
				"items": ["Employee Transfer","Employee Promotion","Employee Separation", "Exit Interview"],
			},
			{"label": _("Employee Claims"), "items": ["Expense Claim", "Travel Claim", "Employee Advance","Employee Benefits"]},
			{
				"label": _("Payroll"),
				"items": [
					"Salary Structure",
					"Salary Slip",
				],
			},
			{
				"label": _("Training"),
				"items": ["Training Event", "Training Result", "Training Feedback", "Employee Skill Map"],
			},
		],
	}


def get_dashboard_for_holiday_list(data):
	data["non_standard_fieldnames"].update({"Leave Period": "optional_holiday_list"})

	data["transactions"].append({"items": ["Leave Period", "Shift Type"]})

	return data


def get_dashboard_for_timesheet(data):
	data["transactions"].append({"label": _("Payroll"), "items": ["Salary Slip"]})

	return data


def get_dashboard_for_project(data):
	data["transactions"].append(
		{"label": _("Claims"), "items": ["Expense Claim"]},
	)

	return data
