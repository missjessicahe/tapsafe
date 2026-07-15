import time
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db, log_event

bp = Blueprint("main", __name__)


def ip() -> str:
    """Return the best available source IP for local audit logging."""
    return (
        request.headers.get("X-Forwarded-For")
        or request.remote_addr
        or "unknown"
    ).split(",")[0].strip()


def limited(token: str, source: str) -> bool:
    """Return True when this token/source pair exceeded the local PIN limit."""
    now = int(time.time())
    db = get_db()
    db.execute(
        "DELETE FROM failed_attempts WHERE ts_epoch < ?",
        (now - current_app.config["RATE_LIMIT_WINDOW_SECONDS"],),
    )
    count = db.execute(
        "SELECT COUNT(*) c FROM failed_attempts WHERE token=? AND source_ip=?",
        (token, source),
    ).fetchone()["c"]
    db.commit()
    return count >= current_app.config["RATE_LIMIT_MAX"]


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/baseline/<card_id>")
def baseline(card_id):
    card = get_db().execute(
        "SELECT * FROM cards WHERE card_id=?", (card_id,)
    ).fetchone()
    if not card:
        abort(404)
    # Deliberately insecure comparison condition: no revocation check and all
    # profile fields are exposed to anyone who knows the permanent URL.
    return render_template("baseline.html", card=card)


@bp.get("/nfc/<token>")
def nfc_entry(token):
    """Dedicated URL encoded on the physical NFC card.

    This route logs a physical-card entry separately, then redirects to the
    normal defended profile route. It does not trust possession of the card as
    authorization for protected information.
    """
    db = get_db()
    card = db.execute("SELECT * FROM cards WHERE token=?", (token,)).fetchone()
    source = ip()

    if not card:
        log_event("nfc_tap", None, source, "denied", "unknown token")
        abort(404)

    outcome = "allowed" if card["active"] else "denied"
    details = "physical NFC entry route" if card["active"] else "card revoked"
    log_event("nfc_tap", card["card_id"], source, outcome, details)

    flash("NFC card detected.", "success")
    return redirect(url_for("main.tap", token=token, from_nfc="1"))


@bp.route("/tap/<token>", methods=["GET", "POST"])
def tap(token):
    db = get_db()
    card = db.execute("SELECT * FROM cards WHERE token=?", (token,)).fetchone()
    source = ip()

    if not card:
        log_event("tap", None, source, "denied", "unknown token")
        abort(404)

    if not card["active"]:
        log_event("tap", card["card_id"], source, "denied", "revoked")
        return render_template("revoked.html"), 403

    protected = False
    rate_limited = False
    arrived_from_nfc = request.args.get("from_nfc") == "1"

    if request.method == "POST":
        if limited(token, source):
            rate_limited = True
            log_event(
                "protected_access",
                card["card_id"],
                source,
                "rate_limited",
                "too many failed PIN attempts",
            )
            return (
                render_template(
                    "tap.html",
                    card=card,
                    protected=False,
                    rate_limited=True,
                    arrived_from_nfc=False,
                ),
                429,
            )

        if request.form.get("pin", "") == card["pin"]:
            db.execute(
                "DELETE FROM failed_attempts WHERE token=? AND source_ip=?",
                (token, source),
            )
            db.commit()
            protected = True
            log_event(
                "protected_access", card["card_id"], source, "allowed", "correct PIN"
            )
        else:
            db.execute(
                "INSERT INTO failed_attempts (ts_epoch,token,source_ip) VALUES (?,?,?)",
                (int(time.time()), token, source),
            )
            db.commit()
            flash("Incorrect PIN.", "error")
            log_event(
                "protected_access",
                card["card_id"],
                source,
                "denied",
                "incorrect PIN",
            )
    else:
        log_event("tap", card["card_id"], source, "allowed", "public layer")

    return render_template(
        "tap.html",
        card=card,
        protected=protected,
        rate_limited=rate_limited,
        arrived_from_nfc=arrived_from_nfc,
    )


@bp.get("/admin/cards")
def cards():
    rows = get_db().execute("SELECT * FROM cards").fetchall()
    return render_template("cards.html", cards=rows)


@bp.get("/admin/nfc-setup")
def nfc_setup():
    """Show the exact URL that should be written to the physical NFC card."""
    cards = get_db().execute("SELECT * FROM cards ORDER BY id").fetchall()
    base_url = request.host_url.rstrip("/")
    return render_template("nfc_setup.html", cards=cards, base_url=base_url)


@bp.post("/admin/cards/<int:card_id>/toggle")
def toggle(card_id):
    db = get_db()
    card = db.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not card:
        abort(404)

    active = 0 if card["active"] else 1
    db.execute("UPDATE cards SET active=? WHERE id=?", (active, card_id))
    db.commit()
    log_event(
        "admin_card_state",
        card["card_id"],
        ip(),
        "updated",
        "active" if active else "revoked",
    )
    return redirect(url_for("main.cards"))


@bp.get("/admin/audit")
def audit():
    rows = get_db().execute(
        "SELECT * FROM audit_events ORDER BY id DESC LIMIT 200"
    ).fetchall()
    return render_template("audit.html", events=rows)
