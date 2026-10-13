// Parse-checks every script in a build.  node test/syntax.mjs [build.html]
// --check only parses, so the bare "three" import never has to resolve, and an
// importmap is skipped because it is JSON wearing a <script> tag.
import fs from "fs";
import path from "path";
import os from "os";
import { execFileSync } from "child_process";
import { fileURLToPath } from "url";

const SW = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const arg = process.argv[2] || fs.readdirSync(SW).filter(f => /^SplatWalk_v.*\.html$/.test(f)).sort().pop();
const file = path.isAbsolute(arg) ? arg : path.join(SW, arg);
const html = fs.readFileSync(file, "utf8");
console.log("checking " + path.basename(file));

const re = /<script([^>]*)>([\s\S]*?)<\/script>/gi;
let m, n = 0, bad = 0;
while ((m = re.exec(html))) {
  const attrs = m[1], body = m[2];
  const type = (attrs.match(/type\s*=\s*["']?([\w/+.-]+)/i) || [])[1] || "";
  if (/\bsrc\s*=/.test(attrs) || !body.trim()) continue;
  if (type && !/^module$/i.test(type) && !/javascript|ecmascript/i.test(type)) continue;
  n++;
  const esm = /^module$/i.test(type);
  const tmp = path.join(os.tmpdir(), `splatwalk_chk${process.pid}_${n}.${esm ? "mjs" : "cjs"}`);
  fs.writeFileSync(tmp, body);
  try {
    execFileSync(process.execPath, ["--check", tmp], { stdio: "pipe" });
    console.log(`  script ${n} (${esm ? "module" : "classic"}, ${body.split("\n").length} lines): parses`);
  } catch (e) {
    bad++;
    console.log(`  script ${n}: SYNTAX ERROR\n` + (e.stderr || "").toString().split("\n").slice(0, 12).join("\n"));
  }
  fs.unlinkSync(tmp);
}
console.log(bad ? `\n${bad} of ${n} failed to parse` : `\nall ${n} parse`);
process.exit(bad ? 1 : 0);
