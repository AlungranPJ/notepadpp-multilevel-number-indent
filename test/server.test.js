// Tests for the Notepad++ engine. Run with:  node test/server.test.js
"use strict";
const path = require("path");
const { spawnSync } = require("child_process");
const { handle } = require(path.join(__dirname, "..", "server", "mni-server.js"));

let passed = 0;
let failed = 0;
function check(name, got, want) {
	const a = JSON.stringify(got);
	const b = JSON.stringify(want);
	if (a === b) {
		passed++;
		console.log("  ok   " + name);
	} else {
		failed++;
		console.log("  FAIL " + name + "\n       expected: " + b + "\n       actual:   " + a);
	}
}
const TAB = { indent: "\t", formats: ["1.", "1.1.", "1.1.1.", "1)", "1.1)", "1.1.1)"] };
/* Applies a reply the way the Notepad++ side does: swap whole lines. */
function apply(lines, reply) {
	if (!reply.change) return lines;
	const c = reply.change;
	return lines.slice(0, c.start).concat(c.lines, lines.slice(c.end));
}
function key(state, action) {
	const r = handle(Object.assign({ op: "action", lines: state.lines, line: state.line, ch: state.ch, from: state.line, to: state.line, action, hadSelection: false }, TAB));
	if (!r.handled) return Object.assign({}, state, { unhandled: true });
	const lines = apply(state.lines, r);
	return { lines, line: r.sel ? r.sel.bLine : state.line, ch: r.sel ? r.sel.bCh : state.ch };
}
function type(state, text) {
	const lines = state.lines.slice();
	const l = lines[state.line];
	lines[state.line] = l.slice(0, state.ch) + text + l.slice(state.ch);
	return { lines, line: state.line, ch: state.ch + text.length };
}

console.log("Tab, Enter and Shift+Tab number like the Obsidian plugin");
{
	let s = { lines: ["1. top"], line: 0, ch: 6 };
	s = key(s, "enter");
	check("Enter makes the next number", s.lines, ["1. top", "2. "]);
	check("the caret sits after the number", [s.line, s.ch], [1, 3]);
	s = key(s, "indent");
	check("Tab nests it under the item above", s.lines, ["1. top", "\t1.1. "]);
	s = type(s, "Media");
	s = key(s, "enter");
	s = key(s, "indent");
	s = type(s, "use");
	s = key(s, "enter");
	s = key(s, "indent");
	s = type(s, "a");
	check("level four is 1)", s.lines[3], "\t\t\t1) a");
	s = key(s, "enter");
	s = type(s, "b");
	s = key(s, "enter");
	s = type(s, "c");
	s = key(s, "enter");
	s = key(s, "outdent");
	s = type(s, "problem");
	check("Shift+Tab comes back to 1.1.2.", s.lines[6], "\t\t1.1.2. problem");
	s = key(s, "enter");
	s = key(s, "indent");
	s = type(s, "d");
	check("a new sub-list under 1.1.2. starts at 1)", s.lines[7], "\t\t\t1) d");
	s = key(s, "enter");
	s = type(s, "e");
	check("and carries on 2)", s.lines[8], "\t\t\t2) e");
	const plain = key({ lines: ["just text"], line: 0, ch: 9 }, "indent");
	check("Tab on a line with no number is left to the editor", plain.unhandled, true);
}

console.log("a selected group moves as one and stays selected");
{
	const lines = ["1. a", "2. b", "3. c"];
	const r = handle(Object.assign({ op: "action", lines, line: 1, ch: 0, from: 1, to: 2, action: "indent", hadSelection: true }, TAB));
	check("both lines go in one level, together", apply(lines, r), ["1. a", "\t1.1. b", "\t1.2. c"]);
	check("the selection covers the group", [r.sel.aLine, r.sel.aCh, r.sel.bLine], [1, 0, 2]);
}

console.log("menu commands");
{
	const lines = ["1. a", "\t1.1. b", "\t\t1.1.1. c", "\t\t\t1) x", "\t\t\t2) y", "\t\t1.1.2. d", "\t\t\t3) z"];
	const r = handle(Object.assign({ op: "renumber", lines, from: 0, to: 6 }, TAB));
	check("Reset numbering restarts a new sub-list at 1)", apply(lines, r)[6], "\t\t\t1) z");
	const add = handle(Object.assign({ op: "insert", lines: ["alpha", "beta"], from: 0, to: 1 }, TAB));
	check("Add numbering", apply(["alpha", "beta"], add), ["1. alpha", "2. beta"]);
	const rem = handle(Object.assign({ op: "remove", lines: ["1. alpha", "2. beta"], from: 0, to: 1 }, TAB));
	check("Remove numbering", apply(["1. alpha", "2. beta"], rem), ["alpha", "beta"]);
	const ing = handle(Object.assign({ op: "ingest", lines: ["1. Intro", "1.1 Scope", "2. Method"], from: 0, to: 2 }, TAB));
	check("Convert to numbered list reads dotted numbers as levels", apply(["1. Intro", "1.1 Scope", "2. Method"], ing), ["1. Intro", "\t1.1. Scope", "2. Method"]);
}

console.log("the stdin/stdout protocol");
{
	const req = [JSON.stringify(Object.assign({ id: 7, op: "action", lines: ["1. a"], line: 0, ch: 4, from: 0, to: 0, action: "enter", hadSelection: false }, TAB)), "not json"].join("\n") + "\n";
	const p = spawnSync(process.execPath, [path.join(__dirname, "..", "server", "mni-server.js")], { input: req, encoding: "utf8" });
	const replies = p.stdout.trim().split("\n").map((l) => JSON.parse(l));
	check("one reply per request line", replies.length, 2);
	check("the reply keeps the request id", replies[0].id, 7);
	check("the reply carries the new lines", replies[0].change.lines, ["2. "]);
	check("a bad line gets an error, not a crash", replies[1].handled === false && typeof replies[1].error, "string");
}

console.log("a byte order mark in front of a request");
{
	const srv = path.join(__dirname, "..", "server", "mni-server.js");
	const p = spawnSync(process.execPath, [srv], { input: "\uFEFF" + JSON.stringify({ id: 1, op: "ping" }) + "\n", encoding: "utf8" });
	const reply = JSON.parse(p.stdout.trim());
	check("a BOM from PowerShell is ignored", reply.handled, true);
	const c = spawnSync(process.execPath, [srv, "--check"], { encoding: "utf8", timeout: 10000 });
	check("--check answers and exits without stdin", JSON.parse(c.stdout.trim()).handled, true);
}

console.log("\n" + passed + " passed, " + failed + " failed");
if (failed) process.exit(1);
