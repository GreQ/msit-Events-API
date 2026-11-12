# Evently API

Flask REST API for events and RSVPs (JWT auth, SQLite). It is a teaching project: the
security weaknesses listed in README "Security Notes" are deliberate and get fixed in
later lessons. Don't harden them unless asked; mention them instead.

## Running

- Virtualenv is `.venv/` (not `venv/` as the README says): `.venv/Scripts/python.exe app.py`
  serves on port 5000. Swagger UI is at `/apidocs`.
- The DB is `instance/events.db` (gitignored). Tables come from `db.create_all()` in
  `create_app()`; there are no migrations, so schema changes need the DB file deleted.
- No test suite. To check a change, use `app.test_client()` with
  `config.Config.SQLALCHEMY_DATABASE_URI = "sqlite://"` set before `create_app()`.

## Conventions

- SQLAlchemy 2.0 style only (Flask-SQLAlchemy 3.1, `db = SQLAlchemy(model_class=Base)`):
  - Columns: `Mapped[...]` + `mapped_column()`; nullability comes from `Optional[...]`.
  - Relationships: explicit `back_populates` on both sides, no `backref`.
  - Queries: `db.session.scalar(s)(db.select(...))`, `db.get_or_404(Model, id)`.
    Never `Model.query`.
- `openapi.yaml` is hand-written; update it whenever an endpoint's request or response changes.
- Error responses are `jsonify({'error': ...}), <status>`.

## Gotchas

- The first registered user becomes admin (`routes/auth.py`).
- JWT identity is the user id as a string; claims carry `is_admin`.
- Known bug: in `rsvp()` the capacity check runs before the existing-RSVP lookup, so a
  user can't change their RSVP once the event is full.
