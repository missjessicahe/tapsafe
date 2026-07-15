from flask import Flask
from .routes import bp
from .db import init_db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="local-demo-only",
        DATABASE="tapsafe.db",
        RATE_LIMIT_MAX=5,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )
    if test_config:
        app.config.update(test_config)
    app.register_blueprint(bp)
    with app.app_context():
        init_db()
    return app
