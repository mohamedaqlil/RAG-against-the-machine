import json
import os

# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# CODE_PATH = os.path.join(PROJECT_ROOT, "datasets_public", "public", "AnsweredQuestions", "dataset_code_public.json")
# DOCS_PATH = os.path.join(PROJECT_ROOT, "datasets_public", "public", "AnsweredQuestions", "dataset_docs_public.json")

# with open(CODE_PATH, "r", encoding="utf-8") as f:
#     code_eval = json.load(f)

# with open(DOCS_PATH, "r", encoding="utf-8") as f:
#     docs_eval = json.load(f)

# code_questions = code_eval["rag_questions"]
# docs_questions = docs_eval["rag_questions"]


# question = docs_questions[0]


def ranges_overlap(ref_start, ref_end, ret_start, ret_end):
    return not (ret_end < ref_start or ret_start > ref_end)


# print(ranges_overlap(1000, 1500, 1200, 1700)) #→ True
# print(ranges_overlap(1000, 1500, 1600, 1800)) #→ False
