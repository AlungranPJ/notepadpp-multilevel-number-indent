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
	const rl = readline.createInterface({ input: process.stdin });
	rl.on("line", (line) => {
		let reply;
		try {
			const req = JSON.parse(line);
			reply = Object.assign({ id: req.id }, handle(req));
		} catch (e) {
			reply = { handled: false, error: String((e && e.stack) || e) };
		}
		process.stdout.write(JSON.stringify(reply) + "\n");
	});
	if (process.argv.includes("--check")) fs.writeSync(1, JSON.stringify(handle({ op: "ping" })) + "\n");
}
