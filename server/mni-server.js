// Multilevel Number Indent for Notepad++: the numbering engine.
//
// Notepad++ talks to this process over stdin/stdout, one JSON object per line.
// The engine itself is the Obsidian plugin's main.js, loaded unchanged with
// the host modules stubbed, so both editors number lists exactly the same way
// and share one tested core. Nothing here touches files; it only answers
// "given these lines and this caret, what should the lines become?".
"use strict";
const fs = require("fs");
const path = require("path");
const readline = require("readline");
const Module = require("module");

function loadCore(file) {
	const deep = () =>
		new Proxy(function () {}, {
			get: (_, key) => {
				if (key === "__esModule") return false;
				if (typeof key === "symbol" || key === "then") return undefined;
				if (key === "prototype") return {};
				return deep();
			},
			apply: () => deep(),
			construct: () => deep(),
		});
	const classes = {};
	const keepDeep = ["Prec", "ViewPlugin", "Decoration", "EditorView", "EditorState", "StateField", "StateEffect", "Facet", "RangeSetBuilder", "RectangleMarker", "keymap"];
	const stub = new Proxy(
		{},
		{
			get: (_, key) => {
				if (key === "__esModule") return false;
				if (typeof key === "symbol") return undefined;
				if (/^[A-Z]/.test(key) && !keepDeep.includes(key)) {
					if (!classes[key]) classes[key] = class {};
					return classes[key];
				}
				return deep();
			},
		}
	);
	const load = Module._load;
	Module._load = (req, ...rest) => (req === "obsidian" || req.startsWith("@codemirror/") ? stub : load(req, ...rest));
	try {
		return require(file).__core;
	} finally {
		Module._load = load;
	}
}

const core = loadCore(process.env.MNI_CORE || path.join(__dirname, "mni-core.js"));

/** The smallest run of whole lines that turns `a` into `b`. */
function lineChange(a, b) {
	let start = 0;
	while (start < a.length && start < b.length && a[start] === b[start]) start++;
	let endA = a.length;
	let endB = b.length;
	while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
		endA--;
		endB--;
	}
	if (start === endA && start === endB) return null;
	return { start, end: endA, lines: b.slice(start, endB) };
}

/** Same rules as the Obsidian plugin's runAction, minus the editor. */
function runAction(req) {
	const before = req.lines;
	const from = req.from;
	const to = req.to;
	const grouped = from < to ? core.applyActionRange(before, from, to, req.action) : null;
	const groupKeys = ["indent", "outdent", "moveUp", "moveDown"];
	const startsGroup = Boolean(core.parseLine(before[from] || "")) && !core.fenceMask(before)[from] && !core.parseHeading(before[from] || "");
	if (from < to && !grouped && groupKeys.includes(req.action) && startsGroup) return { handled: true, change: null, sel: null };
	const result = grouped || core.applyAction(before, req.line, req.ch, req.action);
	if (!result) return { handled: false };
	const change = lineChange(before, result.lines);
	if (!change) return { handled: false };
	const caretLine = result.caretLine === null ? req.line : result.caretLine;
	const lineText = result.lines[caretLine] || "";
	let caretCh = result.caretCh;
	if (caretCh === null) caretCh = core.caretAfter(before[req.line] || "", lineText, req.ch);
	caretCh = Math.min(caretCh, lineText.length);
	const keepGroup = typeof result.selectFrom === "number" && typeof result.selectTo === "number";
	let sel;
	if (keepGroup || (req.hadSelection && req.action !== "enter")) {
		const a = keepGroup ? result.selectFrom : caretLine;
		const b = keepGroup ? result.selectTo : caretLine;
		sel = { aLine: a, aCh: 0, bLine: b, bCh: (result.lines[b] || "").length };
	} else {
		sel = { aLine: caretLine, aCh: caretCh, bLine: caretLine, bCh: caretCh };
	}
	return { handled: true, change, sel };
}

function wholeLines(req, out) {
	if (!out) return { handled: false };
	const change = lineChange(req.lines, out);
	return change ? { handled: true, change, sel: null } : { handled: false };
}

/** Columns in a run of spaces and tabs, the way the core counts an indent. */
function columns(s) {
	let n = 0;
	for (const c of s) n += c === "	" ? 4 : 1;
	return n;
}

/**
 * Enter, two ways. `mode: "next"` is Enter: the engine's own next number.
 * `mode: "body"` is Shift+Enter: the port has no hanging indent of its own, so
 * this starts a body line under the item, indented to where the item's text
 * starts (indent + the width of the number) and carrying the rest of the text
 * when the caret sits mid-line. A body line splits the same way. On a blank
 * body line Enter closes the item and carries on with its next sibling; inside
 * a fence, on an empty item or on plain text nothing is handled.
 */
function enterKey(req) {
	const lines = req.lines;
	const line = req.line;
	const raw = lines[line] || "";
	const mask = core.fenceMask(lines);
	if (mask[line]) return { handled: false };
	const bodyMode = req.mode === "body";
	const plainEnter = () => runAction(Object.assign({}, req, { action: "enter" }));

	const p = core.parseLine(raw);
	if (p) {
		if (!bodyMode) return plainEnter();
		if (p.content.trim() === "") return { handled: false };
		const prefixLength = raw.length - p.content.length;
		if (req.ch < prefixLength) return { handled: false };
		const offset = req.ch - prefixLength;
		const head = p.content.slice(0, offset);
		const hang = p.indent + " ".repeat(p.number.length + 1);
		const tail = p.content.slice(offset);
		const out = lines.slice();
		out[line] = p.indent + p.number + " " + head;
		out.splice(line + 1, 0, hang + tail);
		const caret = hang.length + tail.length;
		return { handled: true, change: lineChange(lines, out), sel: { aLine: line + 1, aCh: caret, bLine: line + 1, bCh: caret } };
	}

	/* An unnumbered line: a body line when a numbered item sits above it. */
	const lead = /^[ 	]*/.exec(raw)[0];
	const leadColumns = columns(lead);
	if (leadColumns === 0) return { handled: false };
	let parent = -1;
	for (let i = line - 1; i >= 0; i--) {
		if (mask[i]) break;
		const above = lines[i] || "";
		if (above.trim() === "") continue;
		const q = core.parseLine(above);
		if (q) {
			if (columns(q.indent) < leadColumns) parent = i;
			break;
		}
		if (columns(/^[ 	]*/.exec(above)[0]) < leadColumns) break;
	}
	if (parent < 0) return { handled: false };
	if (bodyMode) {
		const offset = Math.max(0, Math.min(raw.length - lead.length, req.ch - lead.length));
		const head = raw.slice(lead.length, lead.length + offset);
		const tail = raw.slice(lead.length + offset);
		const out = lines.slice();
		out[line] = lead + head;
		out.splice(line + 1, 0, lead + tail);
		const caret = lead.length + tail.length;
		return { handled: true, change: lineChange(lines, out), sel: { aLine: line + 1, aCh: caret, bLine: line + 1, bCh: caret } };
	}
	if (raw.trim() !== "") return { handled: false };
	const out = lines.slice();
	out[line] = core.parseLine(lines[parent]).indent + "0. ";
	core.renumberRange(out, line, line);
	const change = lineChange(lines, out);
	if (!change) return { handled: false };
	const caret = out[line].length;
	return { handled: true, change, sel: { aLine: line, aCh: caret, bLine: line, bCh: caret } };
}

const RANGE = {
	renumber: (lines, from, to) => {
		const out = lines.slice();
		return core.renumberRange(out, from, to) ? out : null;
	},
	insert: (lines, from, to) => core.insertNumbering(lines, from, to),
	remove: (lines, from, to) => core.removeNumbering(lines, from, to),
	clear: (lines, from, to) => core.clearFormatting(lines, from, to),
	tidy: (lines, from, to) => core.normalizeOutline(lines, from, to),
};

function handle(req) {
	if (req.indent !== undefined || req.formats !== undefined) {
		const cfg = {};
		if (req.indent !== undefined) cfg.indent = req.indent;
		if (req.formats !== undefined) cfg.formats = req.formats;
		core.setConfig(cfg);
	}
	switch (req.op) {
		case "ping":
			return { handled: true, core: fs.readFileSync(path.join(__dirname, "CORE_VERSION"), "utf8").trim() };
		case "action":
			return runAction(req);
		case "enter":
			return enterKey(req);
		case "renumber":
		case "insert":
		case "remove":
		case "clear":
		case "tidy":
			return wholeLines(req, RANGE[req.op](req.lines, req.from, req.to));
		case "ingest": {
			const out = req.lines.slice(0, req.from).concat(core.ingestOutline(req.lines.slice(req.from, req.to + 1).join("\n")), req.lines.slice(req.to + 1));
			return wholeLines(req, out);
		}
		case "numberHeadings":
			return wholeLines(req, core.numberHeadings(req.lines));
		case "removeHeadingNumbers":
			return wholeLines(req, core.removeHeadingNumbers(req.lines));
		case "level": {
			const out = core.setLevel(req.lines, req.line, req.depth);
			return out ? wholeLines(req, out.lines || out) : { handled: false };
		}
		case "clean":
			return { handled: true, text: core.cleanForExport(req.text) };
		default:
			return { handled: false, error: "unknown op " + req.op };
	}
}

module.exports = { handle, lineChange, core };

if (require.main === module) {
	if (process.argv.includes("--check")) {
		fs.writeSync(1, JSON.stringify(handle({ op: "ping" })) + "\n");
		process.exit(0);
	}
	const rl = readline.createInterface({ input: process.stdin });
	rl.on("line", (line) => {
		let reply;
		try {
			// Some shells (Windows PowerShell with a UTF-8 $OutputEncoding) put a BOM in front of piped text.
			const req = JSON.parse(line.replace(/^\uFEFF/, ""));
			reply = Object.assign({ id: req.id }, handle(req));
		} catch (e) {
			reply = { handled: false, error: String((e && e.stack) || e) };
		}
		process.stdout.write(JSON.stringify(reply) + "\n");
	});
}
