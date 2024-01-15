from frappe import _


def get_data():
    return {
        "fieldname": "bulk_leave_encashment",
        "non_standard_fieldnames": {
            "Journal Entry": "reference_name",
        },
        "transactions": [
            {"label": _("Related Transaction"), "items": ["Journal Entry"]},
        ],
    }