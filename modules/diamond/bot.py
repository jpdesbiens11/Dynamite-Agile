"""What Bob le mineur says about Diamond (0.60.36, D-O-044, hook of core/bot.py): the figures, what a review would ask,
the risks and DFMEA rows to act on -- each with a pointer link that opens the page and shows the item."""
from . import export_data as X


def bot_summary(conn, pid, key, link):
    data = X.gather(conn, pid)
    sm = data["summary"]
    pages = {"tree": "#/diamond/{}/ftree", "structure": "#/diamond/{}/fstructure", "risks": "#/diamond/{}/prisk", "dfmea": "#/diamond/{}/dfmea"}
    review = [{"section": sec, "advice": c, "url": link(pages[sec].format(key))}
              for sec in pages for c in data["checks"][sec][:6]]
    risks = [{"code": "R-{}".format(r["number"]), "title": r["title"], "score": r["score"], "level": r["level"]["label"],
              "owner": r["owner_name"] or "", "action": r["action"],
              "url": link(pages["risks"].format(key), "R-{}".format(r["number"]), "Risque {} : {}".format(r["level"]["label"].lower(), r["title"]))}
             for r in sorted(data["risks"], key=lambda r: -r["score"]) if r["level"]["key"] in ("critique", "eleve")]
    high = [{"line": d["line"], "function": "F{} {}".format(d["function_number"], d["function_text"]) if d["function_number"] else "",
             "failure_mode": d["failure_mode"], "ap": d["ap"],
             "url": link(pages["dfmea"].format(key), d["failure_mode"][:80], "AP High : une action est attendue")}
            for d in data["dfmea"] if d["ap"] == "H"]
    # 0.60.38 (D-O-047): who does what, by when -- « Bob, qu'est-ce que Léa a à faire ? », « quoi est en retard ? »
    actions = [{"code": "R-{}".format(r["number"]), "action": r["action"], "owner": r["owner_name"] or "", "due": r["due_date"],
                "late": r["late"], "status": r["status"], "ticket": r["ticket"]["key"] if r["ticket"] else "",
                "url": link(pages["risks"].format(key), "R-{}".format(r["number"]), "Action : " + r["action"][:80])}
               for r in data["risks"] if r["action"].strip() and r["status"] != "closed"]
    actions += [{"code": "DFMEA L{}".format(d["line"]), "action": d["action"], "owner": d["action_owner_name"] or "",
                 "due": d["action_due"], "late": d["late"], "status": d["action_status"], "ticket": d["ticket"]["key"] if d["ticket"] else "",
                 "url": link(pages["dfmea"].format(key), d["failure_mode"][:80], "Action : " + d["action"][:80])}
                for d in data["dfmea"] if d["action"].strip() and d["action_status"] != "done"]
    actions.sort(key=lambda a: (not a["late"], a["due"] or "9999"))
    return {"figures": sm, "review": review, "risks_to_act_on": risks[:10], "dfmea_ap_high": high[:10], "actions": actions[:40],
            "functions": [{"code": X.code(f), "text": f["text"], "level": X.label_of(f, data), "critical": bool(f["critical"]),
                           "url": link(pages["tree"].format(key), X.code(f))} for f in data["tree"]][:60],
            "export": link("#/diamond/{}/dexport".format(key))}
