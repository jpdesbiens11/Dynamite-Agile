"""FR | EN maintenance (0.60.67): visit every screen of a local dev server (http://127.0.0.1:8091) in English, as a guest and as
admin, and list the French originals still shown (DA.i18nScan). Needs Playwright and Chrome; writes /tmp/i18n/crawl_fr.json."""
import json, re, sys
from playwright.sync_api import sync_playwright
FR = re.compile(r"\b(le|la|les|des|du|une|est|pour|avec|dans|sur|qui|que|et|au|aux|ou|ce|cette|vos|votre|chaque|pas|sont)\b", re.I)
ACC = re.compile(r"[àâçéèêëîïôûùœ]")
START = ["#/dashboard", "#/debuter", "#/dynamite/DEMO", "#/agile/DEMO", "#/goldmine/DEMO", "#/diamond/DEMO/story", "#/exploration/DEMO/plan",
         "#/testing/DEMO", "#/tools/DEMO", "#/tools/generator", "#/training", "#/timesheet", "#/help", "#/about", "#/search/?adv=1"]
found = {}
JS = """(()=>{const out=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 for(let n=w.nextNode();n;n=w.nextNode()){const p=n.parentElement; if(!p||p.closest('script,style,code,pre,[contenteditable],[data-no-i18n]')) continue;
  if(!p.getClientRects().length) continue; const t=n.nodeValue.trim(); if(t.length>1) out.push(t)}
 document.querySelectorAll('[placeholder],[title],[aria-label],[data-tip]').forEach(e=>['placeholder','title','aria-label','data-tip'].forEach(a=>{const v=e.getAttribute(a); if(v) out.push(v.trim())}));
 return out})()"""
LINKS = """[...document.querySelectorAll('#main a[href^="#/"], .ag-sidebar a[href^="#/"], nav a[href^="#/"]')].map(a=>a.getAttribute('href'))"""
def run(who):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto("http://127.0.0.1:8091/"); pg.wait_for_timeout(1000)
        if who == "guest":
            pg.click("text=Entrer en invité"); pg.wait_for_timeout(2500)
            if pg.locator(".gt-lang button[lang=en]").count(): pg.click(".gt-lang button[lang=en]"); pg.wait_for_timeout(1000)
            pg.evaluate("DA.guestTour && DA.guestTour.close()")
        else:
            pg.fill("input[autocomplete=username]", "admin"); pg.fill("input[type=password]", "admin"); pg.keyboard.press("Enter"); pg.wait_for_timeout(2500)
            if pg.evaluate("DA.lang()") != "en": pg.click("button.tb-lang"); pg.wait_for_timeout(1500)
        queue, seen = list(START) + (["#/admin/users"] if who == "admin" else []), set()
        while queue and len(seen) < 140:
            h = queue.pop(0)
            if h in seen or re.search(r"/(new|edit)\b|export|\.(csv|xlsx|docx|pdf)", h): continue
            seen.add(h)
            try:
                pg.evaluate("location.hash = %r" % h); pg.wait_for_timeout(1800)
                for orig, shown in pg.evaluate("DA.i18nScan()"):
                    if (len(FR.findall(shown)) >= 1 and ACC.search(shown)) or len(FR.findall(shown)) >= 2:
                        found.setdefault(orig, h)
                for l in pg.evaluate(LINKS):
                    base = re.sub(r"/(issue|page|test)/\d+.*", r"/\1/1", l)
                    if base not in seen and l not in seen and len(queue) < 400 and (base == l or base not in queue): queue.append(l if base == l else l)
            except Exception as e:
                print("skip", h, str(e)[:80], file=sys.stderr)
        b.close()
        print(who, "pages", len(seen), file=sys.stderr)
run("guest"); run("admin")
__import__("os").makedirs("/tmp/i18n", exist_ok=True)
json.dump(found, open("/tmp/i18n/crawl_fr.json", "w"), ensure_ascii=False, indent=0)
print(len(found), sum(len(k) for k in found))
