// Builds dist/npp-multilevel-number-indent.zip: the folder users download.
// Uses PowerShell's Compress-Archive, so it runs on Windows without extra packages.
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const root = path.join(__dirname, "..");
const name = "npp-multilevel-number-indent";
const dist = path.join(root, "dist");
const stage = path.join(dist, name);
const files = [
  "install.cmd", "install.ps1", "uninstall.cmd", "uninstall.ps1", "README.md", "LICENSE", "CHANGELOG.md",
  "docs/README.th.md",
  "server/mni-server.js", "server/mni-core.js", "server/CORE_VERSION",
  "pythonscript/mni_npp.py", "pythonscript/startup_snippet.py",
];
for (const f of fs.readdirSync(path.join(root, "pythonscript/commands"))) files.push("pythonscript/commands/" + f);

fs.rmSync(dist, { recursive: true, force: true });
for (const f of files) {
  const to = path.join(stage, f);
  fs.mkdirSync(path.dirname(to), { recursive: true });
  let text = fs.readFileSync(path.join(root, f));
  // .cmd and .ps1 run on Windows: give them CRLF whatever git checked out.
  if (/\.(cmd|ps1)$/.test(f)) text = Buffer.from(text.toString("utf8").replace(/\r?\n/g, "\r\n"), "utf8");
  fs.writeFileSync(to, text);
}
const zip = path.join(dist, name + ".zip");
// Compress-Archive on Windows PowerShell 5 writes "\\" into entry names; build entries by hand with "/".
const ps = `
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$root = '${dist}'
$zip = [System.IO.Compression.ZipFile]::Open('${zip}', 'Create')
try {
  Get-ChildItem -Recurse -File '${stage}' | ForEach-Object {
    $name = $_.FullName.Substring($root.Length + 1).Replace('\\', '/')
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $name, 'Optimal')
  }
} finally { $zip.Dispose() }`;
execFileSync("powershell", ["-NoProfile", "-Command", ps], { stdio: "inherit" });
for (const f of ["install.ps1", "uninstall.ps1"]) fs.copyFileSync(path.join(stage, f), path.join(dist, f));
console.log(`built ${path.relative(root, zip)} (${files.length} files, ${fs.statSync(zip).size} bytes)`);
