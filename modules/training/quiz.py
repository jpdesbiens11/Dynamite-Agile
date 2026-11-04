"""Multiple-choice tests of the Training topics (D-A-045), written as simple Markdown:

    # Quiz : Timesheet — déclarer ses heures
    pass: 80
    ## Quelle description est acceptée pour soumettre la semaine ?
    - [ ] Aucune, elle est facultative
    - [x] Une courte description du travail fait
    > La semaine ne se soumet pas tant qu'une plage n'a pas de description.

« ## » starts a question, « - [x] » is a right answer (one or more), « - [ ] » a wrong one, « > » the explanation
shown after the test, « pass: » the pass mark in % (80 by default). 10 to 20 questions are recommended per topic.
The browser never receives the answers before grading; grading is done here. Below the pass mark, the missed
questions come back until each one is answered right (circle-back, circle.py, 0.50.10).
"""
import re

from core.errors import ApiError

MAX_QUESTIONS = 60
RECOMMENDED = (10, 20)
OPTION = re.compile(r"^- \[( |x|X)\]\s+(.+)$")


def parse(text):
    """-> {"title", "pass", "questions": [{"text", "options": [{"text", "right"}], "explain"}]}, problems"""
    title, pass_mark, questions, problems = "", 80, [], []
    current = None
    for n, raw in enumerate((text or "").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            current = {"text": line[3:].strip(), "options": [], "explain": "", "line": n}
            questions.append(current)
        elif line.startswith("# "):
            title = line[2:].strip()
        elif line.lower().startswith("pass:"):
            try:
                pass_mark = int(line.split(":", 1)[1].strip().rstrip("%"))
            except ValueError:
                problems.append("Ligne {} : « {} » — pass: attend un nombre de 0 à 100 (ex. pass: 80).".format(n, line[:40]))
        elif OPTION.match(line):
            if current is None:
                problems.append("Ligne {} : réponse avant la première question. Correctif : commencez par « ## Question ».".format(n))
                continue
            m = OPTION.match(line)
            current["options"].append({"text": m.group(2).strip(), "right": m.group(1).lower() == "x"})
        elif line.startswith(">"):
            if current is not None:
                current["explain"] = (current["explain"] + " " + line[1:].strip()).strip()
        else:
            problems.append("Ligne {} : « {} » non reconnue. Correctif : « ## » question, « - [x] » bonne réponse, "
                            "« - [ ] » mauvaise réponse, « > » explication.".format(n, line[:40]))
    if not 0 <= pass_mark <= 100:
        problems.append("pass: {} hors plage. Correctif : de 0 à 100.".format(pass_mark))
    if len(questions) > MAX_QUESTIONS:
        problems.append("{} questions : {} au maximum.".format(len(questions), MAX_QUESTIONS))
    for i, q in enumerate(questions, start=1):
        if len(q["options"]) < 2:
            problems.append("Question {} (ligne {}) : au moins 2 réponses. Correctif : ajoutez des lignes « - [ ] ».".format(i, q["line"]))
        if not any(o["right"] for o in q["options"]):
            problems.append("Question {} (ligne {}) : aucune bonne réponse. Correctif : cochez-en une avec « - [x] ».".format(i, q["line"]))
    return {"title": title, "pass": pass_mark, "questions": questions}, problems


def checked(text):
    """Parsed quiz or 400 listing every problem at once (D-A-031)."""
    quiz, problems = parse(text)
    if problems:
        raise ApiError(400, "QCM refusé — {} problème(s) : {}".format(len(problems), " | ".join(problems[:12])))
    return quiz


def report(text):
    quiz, problems = parse(text)
    count = len(quiz["questions"])
    low, high = RECOMMENDED
    notes = [] if low <= count <= high or not count else ["{} question(s) : {} à {} recommandées par topic.".format(count, low, high)]
    return {"questions": count, "pass": quiz["pass"], "title": quiz["title"], "problems": problems, "notes": notes}


def public(quiz, only=None):
    """Questions for the employee, without the answers. `only`: the original indexes to ask (circle-back round);
    every question carries its original index, the key of the answers sent back."""
    keep = set(range(len(quiz["questions"]))) if only is None else set(only)
    return {"title": quiz["title"], "pass": quiz["pass"], "total": len(quiz["questions"]),
            "questions": [{"index": i, "text": q["text"], "multiple": sum(o["right"] for o in q["options"]) > 1,
                           "options": [o["text"] for o in q["options"]]}
                          for i, q in enumerate(quiz["questions"]) if i in keep]}


def grade(quiz, answers, only=None):
    """answers: {"0": [1], "1": [0, 2], ...} -> score %, right count, per question review (with its original index).
    `only`: grade these original indexes only (circle-back round)."""
    if not isinstance(answers, dict):
        raise ApiError(400, "Réponses attendues : un objet {numéro de question: [réponses cochées]}.")
    asked = range(len(quiz["questions"])) if only is None else sorted(set(only))
    review, right = [], 0
    for i in asked:
        q = quiz["questions"][i]
        given = answers.get(str(i), [])
        if not isinstance(given, list):
            raise ApiError(400, "Question {} : réponses attendues sous forme de liste.".format(i + 1))
        chosen = {int(x) for x in given if str(x).isdigit()}
        good = {j for j, o in enumerate(q["options"]) if o["right"]}
        ok = chosen == good
        right += ok
        review.append({"index": i, "ok": ok, "right": sorted(good), "chosen": sorted(chosen), "explain": q["explain"]})
    total = len(review)
    score = round(100 * right / total) if total else 0
    return {"score": score, "right": right, "total": total, "passed": score >= quiz["pass"], "pass": quiz["pass"],
            "review": review}
