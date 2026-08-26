import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.flags.redirect_location = "/login?redirect-to=/logs"
		raise frappe.Redirect
	context.title = "Lens"
