# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Desuup(Document):
    def validate(self):
        self.validate_address()
        self.update_user()

    def validate_address(self):
        if self.dzongkhag:
            if not self.country:
                self.country = "Bhutan"
            if not frappe.db.exists("Dzongkhags", {"name": self.dzongkhag, "country_name": self.country}):
                frappe.throw("Invalid Dzongkhag")
        if self.gewog:
            if not self.dzongkhag:
                frappe.throw("Dzongkhag is required")
            if not frappe.db.exists("Gewogs", {"name": self.gewog, "dzongkhag": self.dzongkhag}):
                frappe.throw("Invalid Gewog")

        if self.present_dzongkhag:
            if not self.present_country:
                self.country = "Bhutan"
            if not frappe.db.exists("Dzongkhags", {"name": self.present_dzongkhag, "country_name": self.present_country}):
                frappe.throw("Invalid Present Dzongkhag")
        if self.present_gewog:
            if not self.present_dzongkhag:
                frappe.throw("Present Dzongkhag is required")
            if not frappe.db.exists("Gewogs", {"name": self.present_gewog, "dzongkhag": self.present_dzongkhag}):
                frappe.throw("Invalid Present Gewog")
    
    def update_user(self):
        if self.mobile_number and self.user  and self.mobile_number != frappe.db.get_value("Desuup", self.name, "mobile_number"):
            user = frappe.get_doc("User", self.user)
            user.db_set("phone", self.mobile_number, update_modified=False)

@frappe.whitelist()
def create_user(desuup, user=None, email=None):
    emp = frappe.get_doc("Desuup", desuup)
    if not emp.cid_number or len(emp.cid_number) != 11:
        frappe.throw("CID is mandatory to create user")

    #if not emp.email_id:
    #    frappe.throw("Email is mandatory to create user")

    if not emp.mobile_number:
        frappe.throw("Phone number is mandatory to create user")

    user = frappe.new_doc("User")
    user.update(
        {
            "email": emp.email_id.strip() if emp.email_id else "",
            "enabled": 1,
            "is_desuup": 1,
            "first_name": emp.desuup_name.strip() if emp.desuup_name else emp.desuup_name,
            "gender": emp.gender,
            #"birth_date": emp.date_of_birth,
            "phone": emp.mobile_number.removeprefix("+975").removeprefix("975"),
            "username": emp.cid_number.strip() if emp.cid_number else emp.cid_number
        }
    )
    user.append_roles("Desuup")
    user.flags.ignore_permissions = True
    user.flags.no_welcome_mail = True
    emp.db_set("user", emp.cid_number)
    user.insert()
    print("User created for " + emp.name)
    return user.name

def auto_create_users():
    created = failed = pending = 0
    for d in frappe.db.sql("select name from tabDesuup where (user is null or user = '') and mobile_number is not null and mobile_number != '' and cid_number is not null and cid_number != '' and LENGTH(cid_number) = 11", as_dict=1):
        try:
            frappe.db.savepoint("create_desuup_user")
            create_user(d.name)
        except Exception as e:
            frappe.db.rollback(save_point="create_desuup_user")
            failed += 1
            print("Issue creating user for " + str(d.name) + " : " + str(e))
            continue
        created += 1
        pending += 1
        if pending >= 10:
            frappe.db.commit()
            pending = 0
    print(f"Users created : {created}, failed: {failed}")
