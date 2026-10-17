from .rubric import GEvalRubric

CORRECTNESS_RUBRIC = GEvalRubric(
    name="Correctness",
    evaluation_steps=[
        "Compare the actual output directly with the expected output for factual accuracy.",
        "Verify that every required fact, entity, value, and relationship is present and correctly represented.",
        "Verify that the required naming, terminology, and framing are used.",
        "Penalize contradictions, unsupported additions, and misleading details.",
    ],
    evaluation_params=["actual_output", "expected_output"],
)
