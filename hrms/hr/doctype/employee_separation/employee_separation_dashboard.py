from frappe import _


def get_data():
	return {
		"fieldname": "employee_separation",
		"non_standard_fieldnames": {
			"Employee Separation Clearance": "employee_separation_id",
		},
		"transactions": [
			{"label": _("Reference"), "items": ["Employee Separation Clearance", "Exit Interview"]}
		],
	}
