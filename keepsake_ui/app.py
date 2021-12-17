import logging
import threading
import keepsake
from keepsake.daemon import Daemon
from functools import wraps
from datetime import datetime, timedelta
from flask import render_template, Blueprint, Flask


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
    # TODO: experiments - delete
    # TODO: checkpoints - list, delete, download model

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
        chkpoint = exp.best()
        context = dict(
            title="Experiment",
            short_id=exp.short_id(),
            created=exp.created.isoformat(),
            command=exp.command,
            params=sort_by_key(exp.params),
            metrics=sort_by_key(chkpoint.metrics) if chkpoint else {},
        )
        return render_template("experiment.html", **context)

    @bp.route("/experiments", methods=["GET"])
    @handle_error
    def list_experiments():
        experiments = project.experiments.list()
        short_ids = sorted([(e.created.isoformat(), e.short_id())
                            for e in experiments], reverse=True)
        return render_template("experiment_list.html", short_ids=short_ids)

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
