from .rubric import GEvalRubric

COMPLETENESS_RUBRIC = GEvalRubric(
    name="Completeness",
    evaluation_steps=[
        "Identify every distinct part of the question in the input and every required element of the expected output.",
        "Check whether the actual output addresses each part of the question and covers each required element.",
        "Heavily penalize omitted parts, partial answers, and answers that defer or deflect instead of answering.",
        "Do not penalize correct additional detail; judge only coverage, not wording or accuracy of extra content.",
    ],
    evaluation_params=["input", "actual_output", "expected_output"],
)
