from .rubric import GEvalRubric, ScoreBand

CORRECTNESS_RUBRIC = GEvalRubric(
    name="Correctness",
    evaluation_steps=[
        "List the factual claims the actual output makes: values, entities, dates, relationships, and causes.",
        "Compare each claim with the expected output for factual accuracy, and penalize every claim that "
        "contradicts it.",
        "If the expected output lists claims the answer must not make (for example under 'Must not claim'), "
        "heavily penalize an actual output that makes any of them, in any wording.",
        "Penalize details that are accurate on their own but misleading in context.",
        "Do not penalize omissions. A required element that is missing is judged by Completeness, not here.",
        "Do not penalize wording. A fact or mechanism stated in different terms from the expected output is correct.",
        "Do not penalize claims the expected output neither supports nor contradicts.",
    ],
    evaluation_params=["actual_output", "expected_output"],
    score_bands=[
        ScoreBand(
            0,
            2,
            "The main conclusion contradicts the expected output, the output makes a claim it must not make, "
            "or it makes no substantive claim about what the expected output addresses.",
        ),
        ScoreBand(
            3,
            5,
            "The main conclusion agrees with the expected output, but a central value, entity, or cause is "
            "wrong, or several claims contradict it.",
        ),
        ScoreBand(
            6,
            8,
            "The main conclusion and central claims agree with the expected output; one or two minor claims "
            "are wrong or misleading.",
        ),
        ScoreBand(9, 10, "No claim contradicts the expected output, and none is misleading."),
    ],
)
