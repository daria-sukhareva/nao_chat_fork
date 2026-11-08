from cyclopts import App

from .compare import compare
from .cost_report import cost
from .rejudge import rejudge
from .runner import evals as run_evals

evals = App(name="evals", help="Run LLM-as-judge evals.")

evals.command(name="run")(run_evals)
evals.command(name="rejudge")(rejudge)
evals.command(name="cost")(cost)
evals.command(name="compare")(compare)
evals.default(run_evals)

__all__ = ["evals"]
