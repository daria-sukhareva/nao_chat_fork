from cyclopts import App

from .rejudge import rejudge
from .runner import evals as run_evals

evals = App(name="evals", help="Run LLM-as-judge evals.")

evals.command(name="run")(run_evals)
evals.command(name="rejudge")(rejudge)
evals.default(run_evals)

__all__ = ["evals"]
