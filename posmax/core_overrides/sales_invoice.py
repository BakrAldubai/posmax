import frappe
from frappe import _
from frappe.utils import getdate
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.setup.utils import get_exchange_rate
from frappe.utils import (
	add_days,
	add_months,
	cint,
	cstr,
	flt,
	formatdate,
	get_link_to_form,
	getdate,
	nowdate,
)
from erpnext.accounts.utils import get_account_currency, get_fiscal_years, validate_fiscal_year
from erpnext.controllers.accounts_controller import set_balance_in_account_currency
from erpnext.accounts.doctype.sales_invoice.sales_invoice import validate_inter_company_party
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
	get_loyalty_program_details_with_points,
	validate_loyalty_points,
)
from erpnext.accounts.deferred_revenue import validate_service_stop_date
from erpnext.stock.doctype.batch.batch import set_batch_nos


class CustomSalesInvoice(SalesInvoice):
        # POS MAX
	def make_pos_gl_entries(self, gl_entries):
		if cint(self.is_pos):

			skip_change_gl_entries = not cint(frappe.db.get_single_value('Accounts Settings', 'post_change_gl_entries'))
			
			for payment_mode in self.payments:
				if skip_change_gl_entries and payment_mode.account == self.account_for_change_amount:
					payment_mode.base_amount -= flt(self.change_amount)

				if payment_mode.amount:
					payment_mode_account_currency = get_account_currency(payment_mode.account)
					ex_rate = get_exchange_rate(payment_mode_account_currency,self.party_account_currency,self.posting_date)
					# POS, make payment entries
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_to,
							"party_type": "Customer",
							"party": self.customer,
							"against": payment_mode.account,
							"credit": payment_mode.base_amount,
							"credit_in_account_currency": payment_mode.base_amount  \
								if self.party_account_currency==self.company_currency \
								else payment_mode.amount ,
							"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
							"against_voucher_type": self.doctype,
							"cost_center": self.cost_center
						}, self.party_account_currency, item=self)
					)
					
					gl_entries.append(
						self.get_gl_dict({
							"account": payment_mode.account,
							"against": self.customer,
							"conversion_rate":ex_rate,
							"debit": payment_mode.base_amount ,
							"debit_in_account_currency": payment_mode.base_amount  \
								if payment_mode_account_currency==self.company_currency \
								else payment_mode.amount ,
							"cost_center": self.cost_center
						}, payment_mode_account_currency, item=self)
					)

			if not skip_change_gl_entries:
				self.make_gle_for_change_amount(gl_entries)

	def get_gl_dict(self, args, account_currency=None, item=None):
		"""this method populates the common properties of a gl entry record"""

		posting_date = args.get('posting_date') or self.get('posting_date')
		fiscal_years = get_fiscal_years(posting_date, company=self.company)
		if len(fiscal_years) > 1:
			frappe.throw(_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
				formatdate(posting_date)))
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict({
			'company': self.company,
			'posting_date': posting_date,
			'fiscal_year': fiscal_year,
			'voucher_type': self.doctype,
			'voucher_no': self.name,
			'remarks': self.get("remarks") or self.get("remark"),
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening': self.get("is_opening") or "No",
			'party_type': None,
			'party': None,
			'project': self.get("project"),
			'post_net_value': args.get('post_net_value')
		})

		accounting_dimensions = get_accounting_dimensions()
		dimension_dict = frappe._dict()

		for dimension in accounting_dimensions:
			dimension_dict[dimension] = self.get(dimension)
			if item and item.get(dimension):
				dimension_dict[dimension] = item.get(dimension)

		gl_dict.update(dimension_dict)
		gl_dict.update(args)

		if not account_currency:
			account_currency = get_account_currency(gl_dict.account)

		if gl_dict.account and self.doctype not in ["Journal Entry",
			"Period Closing Voucher", "Payment Entry", "Purchase Receipt", "Purchase Invoice", "Stock Entry","Sales Invoice"]:
			self.validate_account_currency(gl_dict.account, account_currency)

		if gl_dict.account and self.doctype not in ["Journal Entry", "Period Closing Voucher", "Payment Entry"]:
			set_balance_in_account_currency(gl_dict, account_currency, self.get("conversion_rate"),
											self.company_currency)

		return gl_dict

	def set_paid_amount(self):
		paid_amount = 0.0
		base_paid_amount = 0.0
		
		for data in self.payments:
			payment_mode_account_currency = get_account_currency(data.account)
			data.payment_mode_currency = payment_mode_account_currency
			ex_rate = get_exchange_rate(payment_mode_account_currency,self.party_account_currency,self.posting_date)
			cex_rate = get_exchange_rate(payment_mode_account_currency,self.company_currency,self.posting_date)
			data.base_amount = flt(data.amount * cex_rate, self.precision("base_paid_amount"))
			paid_amount += data.amount * ex_rate
			base_paid_amount += data.base_amount 

		self.paid_amount = paid_amount
		self.base_paid_amount = base_paid_amount


	def validate(self):
		super(SalesInvoice, self).validate()
		self.validate_auto_set_posting_time()

		if not self.is_pos:
			self.so_dn_required()

		self.set_tax_withholding()

		self.validate_proj_cust()
		self.validate_pos_return()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.check_sales_order_on_hold_or_close("sales_order")
		self.validate_debit_to_acc()
		self.clear_unallocated_advances("Sales Invoice Advance", "advances")
		self.add_remarks()
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_fixed_asset()
		self.set_income_account_for_fixed_assets()
		self.validate_item_cost_centers()
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_invoice_reference)

		if cint(self.is_pos):
			self.validate_pos()

		if cint(self.update_stock):
			self.validate_dropship_item()
			self.validate_item_code()
			self.validate_warehouse()
			self.update_current_stock()
			self.validate_delivery_note()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		if not self.is_opening:
			self.is_opening = 'No'

		if self._action != 'submit' and self.update_stock and not self.is_return:
			set_batch_nos(self, 'warehouse', True)

		if self.redeem_loyalty_points:
			lp = frappe.get_doc('Loyalty Program', self.loyalty_program)
			self.loyalty_redemption_account = lp.expense_account if not self.loyalty_redemption_account else self.loyalty_redemption_account
			self.loyalty_redemption_cost_center = lp.cost_center if not self.loyalty_redemption_cost_center else self.loyalty_redemption_cost_center

		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_sheets_are_submitted()
		self.validate_multiple_billing("Delivery Note", "dn_detail", "amount", "items")
		if not self.is_return:
			self.validate_serial_numbers()
		else:
			self.timesheets = []
		self.update_packing_list()
		self.set_billing_hours_and_amount()
		self.update_timesheet_billing_for_project()
		self.set_status()
		if self.is_pos and not self.is_return:
			self.verify_payment_amount_is_positive()

		#validate amount in mode of payments for returned invoices for pos must be negative
		if self.is_pos and self.is_return:
			self.verify_payment_amount_is_negative()

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points and not self.is_consolidated:
			validate_loyalty_points(self, self.loyalty_points)

		self.reset_default_field_value("set_warehouse", "items", "warehouse")
		# POS MAX
		self.set_paid_amount()





