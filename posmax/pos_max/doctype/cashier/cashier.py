# Copyright (c) 2023, Maktobee and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Cashier(Document):
	def validate(self):
		if self.employee:
			email_id = frappe.get_value("Employee",self.employee,"user_id")
			if email_id:
				self.email_id = email_id

