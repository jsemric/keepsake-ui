import pytest
import time
import keepsake
from keepsake_ui.app import setup_app
from pathlib import Path
from tempfile import TemporaryDirectory


@pytest.fixture(scope="module")
def repo():
    with TemporaryDirectory() as d:
        yield f"file://{d}"


@pytest.fixture(scope="module")
def experiment(repo):
    with TemporaryDirectory() as d:
        path = Path(d)
        with open(path / "s.py", "w") as f:
            f.write("dsada")
        proj = keepsake.Project(repo, d)
        exp = proj.experiments.create(".", params=dict(a=2))

        chkpt = path / "model"
        with open(chkpt, "w") as f:
            f.write("xxx")
        exp.checkpoint(metrics=dict(b=3), path="model")
        exp.stop()
        # wait for daemon to finish
        time.sleep(1)
        yield exp.short_id()


@pytest.fixture(scope="module")
def client(repo):
    app = setup_app(repo)
    with app.test_request_context():
        yield app.test_client()


def test_app(client, experiment):
    resp = client.get("/experiments")
    assert resp.status_code == 200

    resp = client.get(f"/experiments/{experiment}")
    assert resp.status_code == 200

    resp = client.get(f"/experiments/xxxxxx")
    assert resp.status_code == 404
