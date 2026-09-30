from typing import Any

from nao_core.commands.test.runner import ModelConfig


def resolve_judge(judge_model: str) -> Any:
    """Build the DeepEval judge for a 'provider:model_id' string.

    Anthropic models go through a thin client wrapper because DeepEval's native
    AnthropicModel rejects model ids missing from its pricing table.
    """
    config = ModelConfig.parse(judge_model)
    if config.provider == "anthropic":
        return _build_claude_judge(config.model_id)
    return config.model_id


def _build_claude_judge(model_id: str) -> Any:
    import anthropic
    from deepeval.models import DeepEvalBaseLLM

    class ClaudeJudge(DeepEvalBaseLLM):
        def load_model(self):
            return anthropic.Anthropic()

        def generate(self, prompt: str) -> str:
            response = self.load_model().messages.create(
                model=model_id,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        async def a_generate(self, prompt: str) -> str:
            return self.generate(prompt)

        def get_model_name(self) -> str:
            return model_id

    return ClaudeJudge()
