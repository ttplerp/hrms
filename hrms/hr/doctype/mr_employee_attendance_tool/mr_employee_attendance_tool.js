// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('MR Employee Attendance Tool', {
		refresh: function(frm) {
			frm.disable_save();
		},
	
		onload: function(frm) {
			frm.set_value("date", frappe.datetime.get_today());
			// erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
		},
	
		date: function(frm) {
			erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
		},
	
		// branch: function(frm) {
		// 	erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
		// },

		muster_roll_group:  function(frm) {
			erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
		},

		// company: function(frm) {
		// 	erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
		// }
	
	});
	
	
	erpnext.mr_employee_attendance_tool = {
		load_mr_employees: function(frm) {
			if(frm.doc.date) {
				frappe.call({
					method: "hrms.hr.doctype.mr_employee_attendance_tool.mr_employee_attendance_tool.get_mr_employees",
					args: {
						date: frm.doc.date,
						branch: frm.doc.branch,
						muster_roll_group: frm.doc.muster_roll_group,
						company: frm.doc.company
					},
					callback: function(r) {
						if(r.message['unmarked'].length > 0) {
							unhide_field('unmarked_attendance_section')
							if(!frm.mr_employee_area) {
								frm.mr_employee_area = $('<div>')
								.appendTo(frm.fields_dict.mr_employees_html.wrapper);
							}
							frm.MREmployeeSelector = new erpnext.MREmployeeSelector(frm, frm.mr_employee_area, r.message['unmarked'])
						}
						else{
							hide_field('unmarked_attendance_section')
						}
	
						if(r.message['marked'].length > 0) {
							unhide_field('marked_attendance_section')
							if(!frm.marked_mr_employee_area) {
								frm.marked_mr_employee_area = $('<div>')
									.appendTo(frm.fields_dict.marked_attendance_html.wrapper);
							}
							frm.marked_mr_employee = new erpnext.MarkedMREmployee(frm, frm.marked_mr_employee_area, r.message['marked'])
						}
						else{
							hide_field('marked_attendance_section')
						}
					}
				});
			}
		}
	}
	
	erpnext.MarkedMREmployee = class MarkedMREmployee {
		constructor(frm, wrapper, mr_employee) {
			this.wrapper = wrapper;
			this.frm = frm;
			this.make(frm, mr_employee);
		}
		make(frm, mr_employee) {
			var me = this;
			$(this.wrapper).empty();
	
			var row;
			$.each(mr_employee, function(i, m) {
				var attendance_icon = "fa fa-check";
				var color_class = "";
				if(m.status == "Absent") {
					attendance_icon = "fa fa-times"
					color_class = "text-muted";
				}
				else if(m.status == "Half Day") {
					attendance_icon = "fa fa-minus"
				}
	
				if (i===0 || i % 4===0) {
					row = $('<div class="row"></div>').appendTo(me.wrapper);
				}
	
				$(repl('<div class="col-sm-3 %(color_class)s">\
					<label class="marked-mr_employee-label"><span class="%(icon)s"></span>\
					%(mr_employee)s</label>\
					</div>', {
						mr_employee: m.mr_employee +' : '+ m.mr_employee_name,
						icon: attendance_icon,
						color_class: color_class
					})).appendTo(row);
			});
		}
	};
	
	
	erpnext.MREmployeeSelector = class MREmployeeSelector {
		constructor(frm, wrapper, mr_employee) {
			this.wrapper = wrapper;
			this.frm = frm;
			this.make(frm, mr_employee);
		}
		make(frm, mr_employee) {
			var me = this;
	
			$(this.wrapper).empty();
			var employee_toolbar = $('<div class="col-sm-12 top-toolbar">\
				<button class="btn btn-default btn-add btn-xs"></button>\
				<button class="btn btn-xs btn-default btn-remove"></button>\
				</div>').appendTo($(this.wrapper));
	
			var mark_employee_toolbar = $('<div class="col-sm-12 bottom-toolbar">\
				<button class="btn btn-primary btn-mark-present btn-xs"></button>\
				<button class="btn btn-warning btn-mark-half-day btn-xs"></button>\
				<button class="btn btn-danger btn-mark-absent btn-xs"></button>\
				</div>');
	
			employee_toolbar.find(".btn-add")
				.html(__('Check all'))
				.on("click", function() {
					$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
						if(!$(check).is(":checked")) {
							check.checked = true;
						}
					});
				});
	
			employee_toolbar.find(".btn-remove")
				.html(__('Uncheck all'))
				.on("click", function() {
					$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
						if($(check).is(":checked")) {
							check.checked = false;
						}
					});
				});
	
			mark_employee_toolbar.find(".btn-mark-present")
				.html(__('Mark Present'))
				.on("click", function() {
					var mr_employee_present = [];
					$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
						if($(check).is(":checked")) {
							mr_employee_present.push(mr_employee[i]);
						}
					});
					frappe.call({
						method: "hrms.hr.doctype.mr_employee_attendance_tool.mr_employee_attendance_tool.mark_mr_employee_attendance",
						args:{
							"mr_employee_list":mr_employee_present,
							"status":"Present",
							"date":frm.doc.date,
							"company":frm.doc.company
						},
	
						callback: function(r) {
							erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
	
						}
					});
				});
	
			mark_employee_toolbar.find(".btn-mark-absent")
				.html(__('Mark Absent'))
				.on("click", function() {
					var employee_absent = [];
					$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
						if($(check).is(":checked")) {
							employee_absent.push(mr_employee[i]);
						}
					});
					frappe.call({
						method: "hrms.hr.doctype.mr_employee_attendance_tool.mr_employee_attendance_tool.mark_mr_employee_attendance",
						args:{
							"mr_employee_list":employee_absent,
							"status":"Absent",
							"date":frm.doc.date,
							"company":frm.doc.company
						},
	
						callback: function(r) {
							erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
	
						}
					});
				});
	
	
			mark_employee_toolbar.find(".btn-mark-half-day")
				.html(__('Mark Half Day'))
				.on("click", function() {
					var employee_half_day = [];
					$(me.wrapper).find('input[type="checkbox"]').each(function(i, check) {
						if($(check).is(":checked")) {
							employee_half_day.push(mr_employee[i]);
						}
					});
					frappe.call({
						method: "hrms.hr.doctype.mr_employee_attendance_tool.mr_employee_attendance_tool.mark_mr_employee_attendance",
						args:{
							"mr_employee_list":employee_half_day,
							"status":"Half Day",
							"date":frm.doc.date,
							"company":frm.doc.company
						},
	
						callback: function(r) {
							erpnext.mr_employee_attendance_tool.load_mr_employees(frm);
	
						}
					});
				});
	
			var row;
			$.each(mr_employee, function(i, m) {
				if (i===0 || (i % 4) === 0) {
					row = $('<div class="row"></div>').appendTo(me.wrapper);
				}
	
				$(repl('<div class="col-sm-3 unmarked-mr_employee-checkbox">\
					<div class="checkbox">\
					<label><input type="checkbox" class="mr_employee-check" mr_employee="%(mr_employee)s"/>\
					%(mr_employee)s</label>\
					</div></div>', {mr_employee: m.mr_employee +' : '+ m.mr_employee_name})).appendTo(row);
			});
	
			mark_employee_toolbar.appendTo($(this.wrapper));
		}
	};
	