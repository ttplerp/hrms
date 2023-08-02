def get_data():
	return {
		"fieldname": "increment_entry",
		"non_standard_fieldnames": {
			"Journal Entry": "reference_name",
			"Payment Entry": "reference_name",
		},
		"transactions": [{"items": ["Salary Increment"]}],
	}
