from typing import Any

from nao_core.commands.test.runner import ModelConfig

from .cost import TokenUsage

CLAUDE_JUDGE_TEMPERATURE = 0.0
CLAUDE_JUDGE_MAX_TOKENS = 4096


def resolve_judge(judge_model: str) -> Any:
    """Build the DeepEval judge for a 'provider:model_id' string.

    Anthropic models go through a thin client wrapper because DeepEval's native
    AnthropicModel rejects model ids missing from its pricing table.
    """
    config = ModelConfig.parse(judge_model)
    if config.provider == "anthropic":
        return _build_claude_judge(config.model_id)
    return config.model_id


def describe_judge_settings(judge_model: str | None) -> dict[str, Any]:
    if judge_model and ModelConfig.parse(judge_model).provider == "anthropic":
        return {"temperature": CLAUDE_JUDGE_TEMPERATURE, "max_tokens": CLAUDE_JUDGE_MAX_TOKENS}
    return {"temperature": "deepeval default", "max_tokens": "deepeval default"}


def _build_claude_judge(model_id: str) -> Any:
    import anthropic
    from deepeval.models import DeepEvalBaseLLM

    class ClaudeJudge(DeepEvalBaseLLM):
        def __init__(self):
            self.usage = TokenUsage()
            super().__init__(model_id)

        def load_model(self):
            return anthropic.Anthropic()

        def generate(self, prompt: str) -> str:
            response = self.load_model().messages.create(
                model=model_id,
                max_tokens=CLAUDE_JUDGE_MAX_TOKENS,
                temperature=CLAUDE_JUDGE_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )
            self.usage.add(response.usage.input_tokens, response.usage.output_tokens)
            return response.content[0].text

        async def a_generate(self, prompt: str) -> str:
            return self.generate(prompt)

        def get_model_name(self) -> str:
            return model_id

    return ClaudeJudge()
