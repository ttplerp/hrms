def get_data():
	return {
		"fieldname": "employee_advance",
		"non_standard_fieldnames": {
			"Payment Entry": "reference_name",
			"Journal Entry": "reference_name",
		},
		"transactions": [ {"items": ["Journal Entry"]}],
	}
