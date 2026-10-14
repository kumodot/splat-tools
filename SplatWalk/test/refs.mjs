// Every $("id") and getElementById("id") in the build must name an element the
// markup actually has.   node test/refs.mjs [build.html]
//
// This exists because of a real bug: a button was deleted from the markup and
// its handler was left behind. $("toggleUi") returned null, setting .onclick on
// null threw at module top level, and everything after that line never ran. The
// page still LOOKED correct, because the panels are static markup and CSS, so
// three screenshots went by before anyone noticed the renderer was dead. A
// missing id is a syntactically perfect file, so the parse check cannot see it.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const SW = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const arg = process.argv[2] || fs.readdirSync(SW).filter(f => /^SplatWalk_v.*\.html$/.test(f)).sort().pop();
const file = path.isAbsolute(arg) ? arg : path.join(SW, arg);
const html = fs.readFileSync(file, "utf8");
console.log("checking " + path.basename(file));

const defined = new Set();
for (const m of html.matchAll(/\sid\s*=\s*["']([^"']+)["']/g)) defined.add(m[1]);

// Ids the page creates at runtime rather than shipping in the markup.
const RUNTIME_OK = new Set(["takeEmpty"]);

const used = new Map();                       // id -> first line it is used on
const re = /(?:\$\(|getElementById\()\s*["']([^"']+)["']\s*\)/g;
let m;
while ((m = re.exec(html))) {
  if (!used.has(m[1])) used.set(m[1], html.slice(0, m.index).split("\n").length);
}

const missing = [...used].filter(([id]) => !defined.has(id) && !RUNTIME_OK.has(id));
for (const [id, line] of missing) console.log(`  MISSING  $("${id}")  first used at line ${line}`);

// The other direction is a warning, not a failure: markup carries ids that only
// CSS or a label's "for" uses, and that is fine.
const unused = [...defined].filter(id => !used.has(id) && !/^(ui|app)$/.test(id));

console.log(`\n  ${defined.size} ids in markup, ${used.size} referenced from script`);
if (unused.length) console.log(`  ${unused.length} never looked up in script (fine if CSS or labels use them)`);
console.log(missing.length ? `\n${missing.length} dangling reference(s)` : "\nno dangling references");
process.exit(missing.length ? 1 : 0);
