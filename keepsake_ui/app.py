import logging
import threading
import keepsake
from keepsake.daemon import Daemon
from functools import wraps
from datetime import datetime, timedelta
from flask import render_template, Blueprint, Flask, redirect


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
        return render_template("index.html")

    @bp.route("/experiments/<exp_id>", methods=["GET"])
    @handle_error
    def get_experiment(exp_id):
        exp = project.experiments.get(exp_id)
        checkpoints = [
            dict(id=ch.short_id(), created=ch.created, step=ch.step, metrics=ch.metrics)
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
        def extract_experiment_data(exp):
            best = exp.best()
            if best:
                primary_metric = best.primary_metric.get("name")
                score = best.metrics.get(primary_metric)
            else:
                primary_metric = score = None
            return dict(
                created=exp.created.isoformat(),
                short_id=exp.short_id(),
                id=exp.id,
                user=exp.user,
                duration=exp.duration,
                primary_metric=primary_metric,
                score=round(score, 3) if isinstance(score, float) else score,
            )

        experiments = project.experiments.list()
        sorted_experiments = sorted(
            [extract_experiment_data(e) for e in experiments],
            key=lambda x: x["created"],
            reverse=True,
        )
        return render_template("experiment_list.html", experiments=sorted_experiments)

    @bp.route("/error", methods=["GET"])
    def error():
        return render_template("error.html", message="Manually triggered error")

    return bp


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
