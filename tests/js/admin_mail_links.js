/* 0.60.89 (D-O-095): the error of the test e-mail in ⚙ Admin → Courriel shows the SMTP server's answer. Only the pages
   the platform itself points to become links; any other address the server writes stays plain text.
     node tests/js/admin_mail_links.js   (prints "admin_mail links OK" or the failures) */
const fs = require("fs"), vm = require("vm"), path = require("path");

const el = (tag, attrs, ...kids) => ({ tag, attrs: attrs || {}, kids: kids.flat() });
const sandbox = { console, DA: { el, api: {}, clear() {}, field() {}, modal() {}, toast() {} } };
sandbox.window = sandbox; vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "..", "static/js/admin_mail.js"), "utf8"), sandbox);
const linked = sandbox.DA.adminMail.linked;
const failures = [];
const check = (name, ok, got) => { if (!ok) failures.push(name + " -> " + JSON.stringify(got)); };
const links = (parts) => parts.filter((p) => p && p.tag === "a").map((a) => a.attrs.href);
const text = (parts) => parts.map((p) => (typeof p === "string" ? p : p.kids.join(""))).join("");

// 1. the Google page the hints of core/mail.py give: a link, the sentence around it intact
const hint = "534 5.7.9 Application-specific password required. Correctif : https://myaccount.google.com/apppasswords, "
  + "puis collez-le.";
let parts = linked(hint);
check("google page linked", JSON.stringify(links(parts)) === '["https://myaccount.google.com/apppasswords"]', links(parts));
check("google text intact", text(parts) === hint, text(parts));
check("google link opens apart", parts.find((p) => p.tag === "a").attrs.rel === "noopener noreferrer", parts);

// 2. an address written by the SMTP server (its own choice): plain text, never a link
const hostile = "550 Account blocked, unlock at https://evil.example/login?u=admin then retry";
parts = linked(hostile);
check("server address not linked", links(parts).length === 0, parts);
check("server text intact", text(parts) === hostile, text(parts));

// 3. a look-alike of the Google page is not the Google page
parts = linked("see https://myaccount.google.com.evil.example/apppasswords");
check("look-alike not linked", links(parts).length === 0, parts);
parts = linked("see https://myaccount.google.com/apppasswords/../../evil");
check("longer path not linked", links(parts).length === 0, parts);

// 4. javascript: and empty messages
check("javascript: not linked", links(linked("javascript:alert(1)")).length === 0, linked("javascript:alert(1)"));
check("empty message", text(linked(undefined)) === "", linked(undefined));

if (failures.length) { console.log("admin_mail links FAILED\n  " + failures.join("\n  ")); process.exit(1); }
console.log("admin_mail links OK");
