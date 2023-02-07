// Copyright (c) 2023, Maktobee and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cashier', {
	refresh: function(frm) {

	},
	validate:function(frm) {
		frm.trigger('validate_employee');
		frm.trigger('validate_user');
	},
	validate_employee: function(frm){
		frm.toggle_reqd([
			"first_name",
			"gender",
			"date_of_birth",
			"date_of_joining",
			"company"], !frm.doc.employee);
	
	},
	validate_user: function(frm){
		frm.toggle_reqd([
			"first_name",
			"email"], !frm.doc.user_id && !frm.doc.first_name);
	},
	employee:function(frm) {

		if(frm.doc.employee){
			frappe.call({
				method: "frappe.client.get_value",
				args:{
					doctype: "Employee",
					filters: {
						name: frm.doc.employee
					},
					fieldname: [
					"user_id",
					"first_name",
					"last_name",
					"employee_name",
					"company_email",
					"gender",
					"date_of_birth",
					"date_of_joining",
					"branch",
					"company"]
				},
				callback: function(r) {
					if (r.message){
						if (r.message.user_id){
							frm.set_value('user_id', r.message.user_id);
						}
						if (r.message.first_name){
							frm.set_value('first_name', r.message.first_name);
						}
						if (r.message.last_name){
							frm.set_value('last_name', r.message.last_name);
						}
						if (r.message.employee_name){
							frm.set_value('full_name', r.message.employee_name);
						}
						if (r.message.company_email){
							frm.set_value('email', r.message.company_email);
						}
						if (r.message.gender){
							frm.set_value('gender', r.message.gender);
						}
						if (r.message.date_of_birth){
							frm.set_value('date_of_birth', r.message.date_of_birth);
						}
						if (r.message.date_of_joining){
							frm.set_value('date_of_joining', r.message.date_of_joining);
						}
						if (r.message.branch){
							frm.set_value('branch', r.message.branch);
						}
						if (r.message.company){
							frm.set_value('company', r.message.company);
						}

							
							
							

					}

				}
		});
		}
		else{
			if(!frm.doc.user_id){
				frm.set_value('email', '');
				frm.set_value('user_id', '');
			}
			frm.set_value('first_name','');
			frm.set_value('last_name', '');
			frm.set_value('full_name', '');	
			frm.set_value('gender', '');
			frm.set_value('date_of_birth', '');
			frm.set_value('date_of_joining', '');
			frm.set_value('branch', '');
			frm.refresh();

		}
		},

		user_id:function(frm) {
			if(frm.doc.user_id){
				frappe.call({
					method: "frappe.client.get_value",
					args:{
						doctype: "User",
						filters: {
							name: frm.doc.user_id
						},
						fieldname: [
						"email",
						"first_name",
						"last_name",
						"full_name",
						]
					},
					callback: function(r) {
						if (r.message){
					
							if (r.message.email){
								frm.set_value('email', r.message.email);
							}
							if(r.message.first_name && !frm.doc.first_name){
								frm.set_value('first_name', r.message.first_name);
							}
							if(r.message.last_name && !frm.doc.last_name){
								frm.set_value('last_name', r.message.last_name);
							}
							if(r.message.full_name && !frm.doc.full_name){
								frm.set_value('full_name', r.message.full_name);
							}		
	
						}
	
					}
			});
			}
			else{
				frm.refresh();
	
			}
		},

});
