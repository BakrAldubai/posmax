// Copyright (c) 2023, Maktobee and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cashier', {
	refresh: function(frm) {

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
				fieldname: ["user_id"]
			},
			callback: function(r) {
				if (r.message){
					if (r.message.user_id){
						frm.set_value('user_id', r.message.user_id);
					}

				}

			}
		});
	}
	else{
		frm.set_value('user_id', '');

	}
	}

});
