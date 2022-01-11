import logging
import threading
import keepsake
from keepsake.daemon import Daemon
from functools import wraps
from datetime import datetime, timedelta
from flask import render_template, Blueprint, Flask, redirect, request


logger = logging.getLogger(__name__)


class Project(keepsake.Project):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._daemon_start = None
        self._daemon_timeout = timedelta(minutes=1)

    def _daemon(self) -> Daemon:
        with threading.RLock():
            if self._daemon_instance is None:
                self._daemon_start = datetime.utcnow()
                self._daemon_instance = Daemon(self, debug=self._debug)
            elif (datetime.utcnow() - self._daemon_start) > self._daemon_timeout:
                self._daemon_instance.cleanup()
                self._daemon_instance = None
                return self._daemon()
            return self._daemon_instance


def setup_keepsake_blueprint(project: Project):
    bp = Blueprint("keepsake", __name__, template_folder="templates")

    def handle_error(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error(str(e), exc_info=True)
                return render_template("error.html", message=str(e), title="Error"), 404

        return wrapper

    @bp.route("/", methods=["GET"])
    def index():
        return redirect("/experiments")

    @bp.route("/experiments/<exp_id>", methods=["GET"])
    @handle_error
    def get_experiment(exp_id):
        exp = project.experiments.get(exp_id)
        best = exp.best()
        best_id = best.id if best else None
        checkpoints = [
            dict(
                id=ch.short_id(),
                created=ch.created,
                step=ch.step,
                metrics=ch.metrics,
                best=ch.id == best_id,
            )
            for ch in exp.checkpoints
        ]
        all_metrics = sorted({m for ch in checkpoints for m in ch["metrics"]})
        context = dict(
            title="Experiment",
            id=exp.id,
            short_id=exp.short_id(),
            created=exp.created.isoformat(),
            command=exp.command,
            params=sort_by_key(exp.params),
            checkpoints=checkpoints,
            all_metrics=all_metrics,
        )
        return render_template("experiment.html", **context)

    @bp.route("/experiments/<exp_id>/delete", methods=["GET"])
    @handle_error
    def delete_experiment(exp_id):
        exp = project.experiments.get(exp_id)
        exp.delete()
        return redirect("/experiments")

    @bp.route("/experiments", methods=["GET"])
    @handle_error
    def list_experiments():
        experiments = project.experiments.list()
        sorted_experiments = sorted(
            [extract_experiment_data(e) for e in experiments],
            key=lambda x: x["created"],
            reverse=True,
        )
        return render_template("experiment_list.html", experiments=sorted_experiments)

    @bp.route("/experiments/compare", methods=["GET"])
    @handle_error
    def compare_experiments():
        exp_id1 = request.args.get("exp1")
        exp_id2 = request.args.get("exp2")
        if exp_id1 is None or exp_id2 is None:
            experiments = project.experiments.list()
            ids = [e.short_id() for e in experiments]
            return render_template("compare.html", ids=ids)
        exp1 = project.experiments.get(exp_id1)
        exp2 = project.experiments.get(exp_id2)
        exp1_data = extract_experiment_data(exp1)
        exp1_data["params"] = {
            k: v
            for k, v in exp1.params.items()
            if k not in exp2.params or v != exp1.params[k]
        }
        exp2_data = extract_experiment_data(exp2)
        exp2_data["params"] = {
            k: v
            for k, v in exp2.params.items()
            if k not in exp1.params or v != exp2.params[k]
        }
        common_params = sorted(
            set(exp1_data["params"].keys()) | set(exp2_data["params"].keys())
        )
        common_metrics = sorted(
            set(exp1_data["best_metrics"].keys())
            | set(exp2_data["best_metrics"].keys())
        )
        return render_template(
            "compare.html",
            exp1=exp1_data,
            exp2=exp2_data,
            common_params=common_params,
            common_metrics=common_metrics,
        )

    @bp.route("/error", methods=["GET"])
    def error():
        return render_template("error.html", message="Manually triggered error")

    return bp


def extract_experiment_data(exp):
    best = exp.best()
    if best:
        primary_metric = best.primary_metric.get("name")
        score = best.metrics.get(primary_metric)
        best_metrics = best.metrics
    else:
        primary_metric = score = None
        best_metrics = exp.checkpoints[-1].metrics
    return dict(
        created=exp.created.isoformat(),
        short_id=exp.short_id(),
        id=exp.id,
        user=exp.user,
        duration=exp.duration,
        primary_metric=primary_metric,
        best_metrics=best_metrics,
        score=round(score, 3) if isinstance(score, float) else score,
    )


def sort_by_key(d):
    return dict(sorted(d.items()))


def setup_app(repository):
    server = Flask(__name__)

    @server.route("/healthz")
    def healthz():
        return "{status: ok}"

    project = Project(repository=repository)
    bp = setup_keepsake_blueprint(project)
    server.register_blueprint(bp)
    return server


if __name__ == "__main__":
    import os

    app_ = setup_app(os.getenv("REPO"))
    app_.jinja_env.auto_reload = True
    app_.config["TEMPLATES_AUTO_RELOAD"] = True
    app_.run(debug=True)
