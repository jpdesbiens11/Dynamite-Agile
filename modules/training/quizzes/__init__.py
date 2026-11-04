"""Default quizzes of the Training topics (0.50.10, D-B-128): one multiple-choice test of medium difficulty per
topic, in the Markdown format of modules/training/quiz.py, 80 % to pass, circle-back of the missed questions
(circle.py). Every answer is in the reference of the topic (Help chapter, BDC page, TOOLS page).

catalog.ensure() puts a default quiz in a topic whose quiz is empty or still a previous default (UPGRADES); a quiz
edited by an administrator is never replaced.
"""
from . import hl_a, hl_b, hl_c, kb, rh, tl

QUIZZES = {
    "HL-01": hl_a.HL_01, "HL-02": hl_a.HL_02, "HL-03": hl_a.HL_03, "HL-04": hl_a.HL_04, "HL-05": hl_a.HL_05,
    "HL-06": hl_b.HL_06, "HL-07": hl_b.HL_07, "HL-08": hl_b.HL_08, "HL-09": hl_b.HL_09, "HL-10": hl_b.HL_10,
    "HL-11": hl_c.HL_11, "HL-12": hl_c.HL_12, "HL-13": hl_c.HL_13, "HL-14": hl_c.HL_14,
    "KB-01": kb.KB_01, "KB-02": kb.KB_02, "KB-03": kb.KB_03,
    "TL-01": tl.TL_01, "TL-02": tl.TL_02, "TL-03": tl.TL_03, "TL-06": tl.TL_06,
    "RH-01": rh.RH_01, "RH-02": rh.RH_02,
}


def default(code):
    """Default quiz of a topic code ('' when none)."""
    return QUIZZES.get(code, "")
