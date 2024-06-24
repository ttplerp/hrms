frappe.ui.form.on('Employee Alerts', 'refresh', function(frm) {
    frm.set_query('employee', function(doc) {
        return {
            filters: {
                name: doc.employee
            }
        };
    });

    frm.add_fetch('employee', 'employee_name', 'employee.name');
    frm.add_fetch('employee', 'designation', 'employee.designation');
    frm.add_fetch('employee', 'department', 'employee.department');
});

frappe.ui.form.on('Employee Alerts', 'employee', function(frm) {
    if (frm.doc.employee) {
        frm.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Employee',
                name: frm.doc.employee
            },
            callback: function(data) {
                if (data.message) {
                    frm.set_value('employee_name', data.message.name);
                    frm.set_value('designation', data.message.designation);
                    frm.set_value('department', data.message.department);
                }
            }
        });
    } else {
        frm.set_value('employee_name', '');
        frm.set_value('designation', '');
        frm.set_value('department', '');
    }
});
