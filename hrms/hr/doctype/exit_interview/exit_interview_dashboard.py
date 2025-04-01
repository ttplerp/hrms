from frappe import _


def get_data():
	return {
		"fieldname": "exit_interview",
		"transactions": [{"items": ["Employee Separation"]}],
		"reports": [{"label": _("Referneces"), "items": ["Employee Separation"]}],
	}
