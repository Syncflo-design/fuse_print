// Print Floor — each step of a run at its workstation: a station PC with a scanner, a tablet or a phone.
//
// One pattern: scan the job ticket (or type the end of the works order number), or tap the
// workstation; tap Start; at the end say how many good ones went on, tap why any were spoiled,
// Done. Every tap goes through fuse_print.floor, which records it on ERPNext's own job card. The
// last step finishes the run, which backflushes the materials.
//
// Where Nest Assistant is installed the note box gets its mic, so the operator can speak the note.
//
// Mounted in page.body (a jQuery object in v16). Server text always goes through esc().

frappe.pages['fuse-print-floor'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __('Print Floor'), single_column: true });

	const BUILD_MARKER = 'v0.1.0-2026-10-29';
	if (!document.getElementById('fuse-print-floor-stylesheet')) {
		const link = document.createElement('link');
		link.id = 'fuse-print-floor-stylesheet';
		link.rel = 'stylesheet';
		link.href = '/assets/fuse_print/css/fuse_print_floor.css?v=' + encodeURIComponent(BUILD_MARKER);
		document.head.appendChild(link);
	}
	wrapper.printFloor = new PrintFloor(page);
};

frappe.pages['fuse-print-floor'].on_page_show = function (wrapper) {
	// Back on the page: the counts may have moved while it was away. Not on the first show, which
	// follows straight on from the load: a second render would drop a scan already typed in.
	const floor = wrapper.printFloor;
	if (!floor) return;
	if (!floor.shown) { floor.shown = true; return; }
	if (floor.screen === 'home') floor.home();
};

const FP = 'fuse_print.floor.';

// Lucide paths, one stroke weight. Every icon sits beside text, so all are aria-hidden.
const FP_ICONS = {
	back: 'M19 12H5M12 19l-7-7 7-7',
	user: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
	scan: 'M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 12h10',
	play: 'M6 3l14 9-14 9V3z',
	tick: 'M20 6 9 17l-5-5',
	printer: 'M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z',
	alert: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
	camera: 'M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
	box: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16zM3.27 6.96 12 12.01l8.73-5.05M12 22.08V12',
};

function fp_icon(name, cls) {
	return '<svg class="fp-icon ' + (cls || '') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
		'<path d="' + (FP_ICONS[name] || FP_ICONS.alert) + '"></path></svg>';
}

function esc(value) {
	return frappe.utils.escape_html(value == null ? '' : String(value));
}

function fp_num(value) {
	return format_number(flt(value), null, 0);
}

function fp_get(key) {
	try { return localStorage.getItem('fuse_print:' + key) || ''; } catch (e) { return ''; }
}

function fp_set(key, value) {
	try { localStorage.setItem('fuse_print:' + key, value || ''); } catch (e) { /* a locked-down browser is not a reason to stop */ }
}

// A station PC's scanner types into whatever has the focus, so the scan box takes it there. On a
// phone or tablet it does not, or the keyboard would cover the screen.
function fp_touch() {
	return window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
}

function fp_call(method, args) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: FP + method,
			args: args || {},
			callback: (r) => resolve(r.message),
			error: (e) => reject(e),
		});
	});
}

class PrintFloor {
	constructor(page) {
		this.page = page;
		this.ctx = null;
		this.screen = 'home';
		this.ws = null;
		this.$root = $('<div class="fp-root"></div>').appendTo(page.body);
		this.page.set_secondary_action(__('Home'), () => this.home(), 'home');
		this.home();
	}

	// The operator is remembered on the device, as the person at that station.
	get operator() {
		try { return JSON.parse(fp_get('operator') || 'null'); } catch (e) { return null; }
	}

	set operator(op) {
		fp_set('operator', op ? JSON.stringify(op) : '');
	}

	render(html) {
		this.$root.html(html);
		window.scrollTo(0, 0);
	}

	header(title, sub) {
		return '<div class="fp-head"><button type="button" class="fp-back" data-act="back" aria-label="' + esc(__('Back')) + '">' +
			fp_icon('back') + '</button><div><h2>' + esc(title) + '</h2>' + (sub ? '<p>' + esc(sub) + '</p>' : '') + '</div></div>';
	}

	bind_back() {
		this.$root.find('[data-act="back"]').on('click', () => {
			if (this.screen === 'step' && this.ws) this.station(this.ws);
			else this.home();
		});
	}

	operator_bar() {
		const who = this.operator;
		return '<button type="button" class="fp-who" data-act="who">' + fp_icon('user') + '<span>' +
			(who ? __('Working as') + ' <b>' + esc(who.name) + '</b>' : '<b>' + esc(__('Tap to say who is working')) + '</b>') +
			'</span></button>';
	}

	bind_who(then) {
		this.$root.find('[data-act="who"]').on('click', () => this.pick_operator(then));
	}

	need_operator(then) {
		if (this.operator) return then();
		this.pick_operator(then);
	}

	pick_operator(then) {
		const ops = (this.ctx && this.ctx.operators) || [];
		this.screen = 'who';
		this.render([
			this.header(__('Who is working?')),
			'<p class="fp-lead">' + esc(__('Each step records who ran it. Choose your name once; this device remembers it.')) + '</p>',
			ops.length ? '<div class="fp-tiles">' + ops.map((op, i) =>
				'<button type="button" class="fp-tile" data-op="' + i + '">' + fp_icon('user') + '<span>' + esc(op.employee_name) + '</span></button>'
			).join('') + '</div>' : '<p class="fp-lead">' + esc(__('No active employees for this company.')) + '</p>',
		].join(''));
		this.$root.find('[data-act="back"]').on('click', () => this.home());
		this.$root.find('[data-op]').on('click', (e) => {
			const op = ops[Number($(e.currentTarget).attr('data-op'))];
			this.operator = { id: op.name, name: op.employee_name };
			if (then) then(); else this.home();
		});
	}

	// ── home: the scan box and the workstations with work waiting ───────────

	home() {
		this.screen = 'home';
		this.ws = null;
		if (!this.ctx) this.render('<p class="fp-lead">' + esc(__('Loading…')) + '</p>');
		fp_call('bootstrap').then((ctx) => {
			this.ctx = ctx;
			if (this.screen !== 'home') return;
			const stations = ctx.workstations.map((s) => [
				'<button type="button" class="fp-station" data-ws="' + esc(s.workstation) + '">',
				'  <span class="fp-station-icon">' + fp_icon('printer') + '</span>',
				'  <span class="fp-station-name">' + esc(s.workstation) + '<small>' + esc(s.operations.join(', ')) + '</small>',
				s.running ? '<i class="fp-badge">' + esc(__('{0} under way', [s.running])) + '</i>' : '',
				'  </span>',
				'  <span class="fp-count" aria-label="' + esc(__('{0} waiting', [s.ready])) + '">' + s.ready + '</span>',
				'</button>',
			].join('')).join('');
			this.render([
				this.operator_bar(),
				this.scan_html(),
				'<span class="fp-sub">' + esc(__('Work waiting')) + '</span>',
				stations ? '<div class="fp-stations">' + stations + '</div>'
					: '<p class="fp-lead">' + esc(__('Nothing is waiting on the floor.')) + '</p>',
			].join(''));
			this.bind_who();
			this.bind_scan();
			this.$root.find('[data-ws]').on('click', (e) => this.station($(e.currentTarget).attr('data-ws')));
		}).catch(() => {
			if (this.screen !== 'home') return;
			this.render('<p class="fp-warn">' + fp_icon('alert') + esc(__('The floor could not load. Check the connection, then try again.')) + '</p>' +
				'<button type="button" class="fp-go" data-act="retry">' + esc(__('Try again')) + '</button>');
			this.$root.find('[data-act="retry"]').on('click', () => this.home());
		});
	}

	scan_html() {
		// A phone or tablet without a scanner reads the ticket with its camera, through Frappe's own
		// barcode reader where the desk has one.
		const camera = fp_touch() && frappe.barcode && typeof frappe.barcode.scan_barcode === 'function';
		return '<form class="fp-scan" autocomplete="off">' + fp_icon('scan', 'fp-icon-lg') +
			'<input class="fp-scan-input" name="scan" enterkeyhint="go" autocapitalize="characters" spellcheck="false" ' +
			'aria-label="' + esc(__('Job ticket')) + '" placeholder="' + esc(__('Scan the job ticket, or type the end of its number')) + '">' +
			(camera ? '<button type="button" class="fp-scan-cam" data-act="camera" aria-label="' + esc(__('Scan with the camera')) + '">' +
				fp_icon('camera') + '</button>' : '') +
			'<button type="submit" class="fp-scan-go">' + esc(__('Open')) + '</button></form>';
	}

	bind_scan() {
		const $input = this.$root.find('.fp-scan-input');
		const $form = this.$root.find('.fp-scan');
		if (!fp_touch()) $input.trigger('focus');
		$form.on('submit', (e) => {
			e.preventDefault();
			const term = String($input.val() || '').trim();
			if (!term) return;
			fp_call('find', { term: term }).then((name) => {
				this.ws = null;
				this.need_operator(() => this.step(name));
			}).catch(() => $input.trigger('select'));
		});
		this.$root.find('[data-act="camera"]').on('click', () => {
			frappe.barcode.scan_barcode().then((code) => {
				if (!code) return;
				$input.val(code);
				$form.trigger('submit');
			}).catch(() => { /* closed without a read */ });
		});
	}

	// ── a workstation's queue ───────────────────────────────────────────────

	station(ws) {
		this.screen = 'station';
		this.ws = ws;
		this.render(this.header(ws) + '<p class="fp-lead">' + esc(__('Loading…')) + '</p>');
		this.bind_back();
		fp_call('queue', { workstation: ws }).then((rows) => {
			if (this.screen !== 'station' || this.ws !== ws) return;
			const jobs = rows.map((r) => [
				'<button type="button" class="fp-job" data-card="' + esc(r.name) + '">',
				'  <span class="fp-job-main"><b>' + esc(r.work_order) + '</b>' + (r.customer ? ' · ' + esc(r.customer) : ''),
				'    <small>' + esc(r.item_name || r.item_code) + '</small></span>',
				'  <span class="fp-job-side">' + esc(r.operation) + '<b>' + fp_num(r.run) + '</b>',
				r.running ? '<i class="fp-badge fp-badge-go">' + esc(__('Under way')) + '</i>' : '',
				'  </span>',
				'</button>',
			].join('')).join('');
			this.render([
				this.header(ws, __('Runs whose turn it is here')),
				this.operator_bar(),
				jobs ? '<div class="fp-jobs">' + jobs + '</div>' : '<p class="fp-lead">' + esc(__('Nothing is waiting here.')) + '</p>',
			].join(''));
			this.bind_back();
			this.bind_who(() => this.station(ws));
			this.$root.find('[data-card]').on('click', (e) => {
				const name = $(e.currentTarget).attr('data-card');
				this.need_operator(() => this.step(name));
			});
		});
	}

	// ── one step: start it, then say what it passed on and why it spoiled any ──

	step(name) {
		this.screen = 'step';
		this.render('<p class="fp-lead">' + esc(__('Loading…')) + '</p>');
		fp_call('step', { name: name }).then((c) => this.draw_step(c)).catch(() => this.home());
	}

	// Back to a step after choosing who is working.
	redraw(c) {
		this.screen = 'step';
		this.draw_step(c);
	}

	draw_step(c) {
		if (this.screen !== 'step') return;
		const facts = '<div class="fp-facts">' +
			'<div><span>' + esc(__('Product')) + '</span><b>' + esc(c.item_name || c.item_code) + '</b></div>' +
			'<div><span>' + esc(__('Run')) + '</span><b>' + fp_num(c.run) + '</b></div>' +
			'<div><span>' + esc(__('Reached this step')) + '</span><b>' + fp_num(c.received) + '</b></div></div>';
		const top = this.header(c.operation + ' · ' + c.workstation, c.work_order + (c.customer ? ' · ' + c.customer : '')) + facts;

		if (c.docstatus) {
			this.render(top + '<p class="fp-note-line">' + fp_icon('tick') + esc(__('This step is done.')) + '</p>');
		} else if (c.waiting_for) {
			this.render(top + '<p class="fp-warn">' + fp_icon('alert') +
				esc(__('Waiting for {0}: it has to be finished before {1} can start.', [c.waiting_for, c.operation])) + '</p>');
		} else if (!c.started) {
			this.render(top + this.operator_bar() +
				'<button type="button" class="fp-go" data-act="start">' + fp_icon('play', 'fp-icon-lg') + esc(__('Start {0}', [c.operation])) + '</button>');
			this.bind_who(() => this.redraw(c));
			this.$root.find('[data-act="start"]').on('click', (e) => {
				const op = this.operator;
				if (!op) return this.pick_operator(() => this.redraw(c));
				$(e.currentTarget).prop('disabled', true);
				fp_call('start', { job_card: c.name, employee: op.id })
					.then((fresh) => { this.screen = 'step'; this.draw_step(fresh); })
					.catch(() => $(e.currentTarget).prop('disabled', false));
			});
		} else {
			this.draw_finish(c, top);
		}
		this.bind_back();
	}

	draw_finish(c, top) {
		const reasons = (this.ctx && this.ctx.reasons) || [];
		const since = String(c.started || '').slice(11, 16);
		this.render([
			top,
			'<p class="fp-note-line">' + fp_icon('play') + esc(__('Started {0}', [since])) +
				(c.started_by ? ' · ' + esc(c.started_by) : '') + '</p>',
			'<label class="fp-field"><span>' + esc(__('Good ones passed on')) + '</span>',
			'<input type="number" class="fp-good" inputmode="numeric" min="1" step="1" max="' + flt(c.received) + '" value="' + flt(c.received) + '"></label>',
			'<p class="fp-spoiled" aria-live="polite">' + esc(__('Spoiled at this step')) + ': <b class="fp-spoiled-n">0</b></p>',
			'<div class="fp-reasons" hidden><span class="fp-sub">' + esc(__('Why?')) + '</span><div class="fp-chips">',
			reasons.map((r) => '<button type="button" class="fp-chip" aria-pressed="false" data-reason="' + esc(r) + '">' + esc(r) + '</button>').join(''),
			'</div></div>',
			'<label class="fp-field"><span>' + esc(__('Note (optional)')) + '</span>',
			'<textarea class="fp-note" rows="3" placeholder="' + esc(__('Anything the office should know')) + '"></textarea></label>',
			'<button type="button" class="fp-go" data-act="done" disabled>' + fp_icon('tick', 'fp-icon-lg') + esc(__('Done')) + '</button>',
		].join(''));

		const $good = this.$root.find('.fp-good');
		const $done = this.$root.find('[data-act="done"]');
		const $note = this.$root.find('.fp-note');
		let reason = null;

		const update = () => {
			const good = flt($good.val());
			const spoiled = Math.max(flt(c.received) - good, 0);
			this.$root.find('.fp-spoiled-n').text(fp_num(spoiled));
			this.$root.find('.fp-reasons').prop('hidden', !spoiled);
			const ok = good > 0 && good <= flt(c.received) && (!spoiled || !!reason);
			$done.prop('disabled', !ok);
		};
		$good.on('input', update);
		this.$root.find('[data-reason]').on('click', (e) => {
			reason = $(e.currentTarget).attr('data-reason');
			this.$root.find('[data-reason]').attr('aria-pressed', 'false');
			$(e.currentTarget).attr('aria-pressed', 'true');
			update();
		});
		// Nest Assistant's mic, where that app is installed and its mic is on.
		if (frappe.nest_assistant && typeof frappe.nest_assistant.add_mic === 'function') frappe.nest_assistant.add_mic($note);
		update();

		$done.on('click', () => {
			const good = flt($good.val());
			const spoiled = Math.max(flt(c.received) - good, 0);
			$done.prop('disabled', true);
			fp_call('finish', { job_card: c.name, good: good, reason: spoiled ? reason : null, note: $note.val() })
				.then((r) => this.after_finish(r))
				.catch(() => $done.prop('disabled', false));
		});
	}

	after_finish(r) {
		const done = __('{0} done: {1} passed on', [r.operation, fp_num(r.good)]) +
			(r.spoiled ? ', ' + __('{0} spoiled ({1})', [fp_num(r.spoiled), r.reason]) : ', ' + __('nothing spoiled'));
		if (r.next) {
			frappe.show_alert({ message: esc(done + '. ' + __('Next: {0} at {1}.', [r.next.operation, r.next.workstation])), indicator: 'green' }, 7);
			return this.ws ? this.station(this.ws) : this.home();
		}
		this.screen = 'finished';
		let body;
		if (r.finished) {
			body = '<div class="fp-finished">' + fp_icon('box', 'fp-icon-xl') + '<h2>' + esc(__('Run finished')) + '</h2>' +
				'<p>' + esc(__('{0} into {1}. The materials were backflushed on {2}.', [fp_num(r.finished.made), r.finished.warehouse, r.finished.entry])) + '</p></div>';
		} else if (r.finish_error) {
			body = '<p class="fp-warn">' + fp_icon('alert') + esc(__('{0} is recorded, but the run could not be finished: {1} Finish it from works order {2} once that is put right.',
				[r.operation, r.finish_error, r.work_order])) + '</p>';
		} else {
			body = '';
		}
		this.render('<p class="fp-note-line">' + fp_icon('tick') + esc(done) + '.</p>' + body +
			'<button type="button" class="fp-go" data-act="home">' + esc(__('Back to the floor')) + '</button>');
		this.$root.find('[data-act="home"]').on('click', () => this.home());
	}
}
