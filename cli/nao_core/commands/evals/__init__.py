from cyclopts import App

from .runner import evals as run_evals

evals = App(name="evals", help="Run LLM-as-judge evals.")

evals.command(name="run")(run_evals)
evals.default(run_evals)

__all__ = ["evals"]
