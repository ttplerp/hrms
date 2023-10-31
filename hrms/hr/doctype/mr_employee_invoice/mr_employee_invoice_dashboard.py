from frappe import _

def get_data():
	return {
        "fieldname": "mr_employee_invoice",
        "non_standard_fieldnames": {
            "Journal Entry": "reference_doctype",
        },
        "transactions": [
            {"label": _("Related Transaction"), "items": ["Journal Entry"]},
        ],
	}