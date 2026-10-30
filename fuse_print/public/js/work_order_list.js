// The demo loader, on the Fuse demo site only (site config fuse_demo_site) and for a System
// Manager. It never appears on a client's site.
//
// ERPNext and other Fuse apps add their own list settings for Work Order, so this extends them
// rather than replacing them: their onload still runs first.
(() => {
	const settings = (frappe.listview_settings['Work Order'] = frappe.listview_settings['Work Order'] || {});
	const previous = settings.onload;
	settings.onload = function (listview) {
		if (previous) previous.apply(this, arguments);
		if (!frappe.user.has_role('System Manager') || !frappe.boot.fuse_demo_site) return;
		listview.page.add_menu_item(__('Load Sticker Printing Demo'), () => {
			const dialog = new frappe.ui.Dialog({
				title: __('Load Sticker Printing Demo'),
				fields: [
					{
						fieldname: 'presenter', fieldtype: 'Data', label: __('Presenter login'), options: 'Email',
						default: 'sticker_printing@syncflo.co.za',
						description: __('An existing user. Its Fuse Home is set to this profile and its company to Sticker Printing; its roles are left as they are.'),
					},
					{
						fieldname: 'note', fieldtype: 'HTML',
						options: `<p class="text-muted small">${__('History is made on the first load only. Later loads make the live steps again once a demo has used them.')}</p>`,
					},
				],
				primary_action_label: __('Load'),
				primary_action(values) {
					dialog.hide();
					frappe.call({
						method: 'fuse_print.demo.sticker_printing.load', args: { presenter: values.presenter },
						freeze: true, freeze_message: __('Loading the sticker printing demo…'),
					}).then((r) => {
						frappe.msgprint({ title: __('Sticker printing demo loaded'), message: r.message.summary, indicator: 'green' });
						listview.refresh();
					});
				},
			});
			dialog.show();
		});
	};
})();
