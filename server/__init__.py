# server/__init__.py
from flask import Flask
import time
import os


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
    )

    app.start_time = time.time()

    from .routes import bp as server_bp
    app.register_blueprint(server_bp)

    return app
