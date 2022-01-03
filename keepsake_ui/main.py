import argparse
import threading
import time
import webbrowser
from gunicorn.app.base import BaseApplication
from keepsake_ui.app import setup_app


class Application(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

    def init(self, parser, opts, args):
        pass


def parse_args():
    parser = argparse.ArgumentParser()
    default_bind = "0.0.0.0:8080"
    parser.add_argument(
        "-b",
        "--bind",
        type=str,
        help=f"Address port bind (default {default_bind})",
        default=default_bind,
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="If set do not open browser"
    )
    parser.add_argument("-r", "--repository", type=str, help="Keepsake repository")
    return parser.parse_args()


def open_browser(bind):
    time.sleep(1)
    webbrowser.open(bind)


def main():
    args = parse_args()
    options = {
        "bind": args.bind,
        "workers": 1,
    }
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.bind,), daemon=True).start()
    Application(setup_app(args.repository), options).run()


if __name__ == "__main__":
    main()
