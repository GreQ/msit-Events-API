# Evently API

A Flask-based REST API for managing events and RSVPs with different access levels. This API is designed to teach web security best practices through incremental improvements.

## Features

- **Public Events**: Anyone can RSVP without authentication
- **Protected Events**: Requires user authentication to RSVP
- **Admin Events**: Requires admin role to RSVP

## Tech Stack

- Flask 3.0.0
- Flask-SQLAlchemy (SQLite database)
- Flask-CORS
- Flask-JWT-Extended (JWT authentication)

## Setup

1. Create and activate a virtual environment:

   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

   **Linux/Mac:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

```

## Swagger UI Documentation

The API includes interactive Swagger UI documentation. After starting the server:

1. Open your browser and navigate to: `http://localhost:5000/apidocs`

2. You'll see an interactive API documentation interface where you can:
   - Browse all available endpoints
   - See request/response schemas
   - Test endpoints directly from the browser
   - Authenticate using the "Authorize" button (enter your JWT token)

3. To use the "Authorize" button:
   - First, login via `/api/auth/login` to get your JWT token
   - Click the "Authorize" button at the top of the Swagger UI
   - Enter: `Bearer <your_jwt_token>` (replace `<your_jwt_token>` with your actual token)
   - Now you can test protected endpoints directly from Swagger UI

**Alternative**: You can also view the OpenAPI specification directly at `http://localhost:5000/apispec_1.json`

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
  ```json
  {
    "username": "user123",
    "password": "password123"
  }
  ```

- `POST /api/auth/login` - Login and get JWT token
  ```json
  {
    "username": "user123",
    "password": "password123"
  }
  ```

### Events

- `GET /api/events` - Get all events
- `GET /api/events/<id>` - Get a specific event
- `POST /api/events` - Create a new event (requires authentication)
  ```json
  {
    "title": "Python Meetup",
    "description": "Monthly Python developer meetup",
    "date": "2026-01-15T18:00:00",
    "location": "Tech Hub, Room 101",
    "capacity": 50,
    "is_public": true,
    "requires_admin": false
  }
  ```

### RSVPs

- `POST /api/rsvps/event/<event_id>` - RSVP to an event
  ```json
  {
    "attending": true
  }
  ```

- `GET /api/rsvps/event/<event_id>` - Get all RSVPs for an event

## Authentication

For protected endpoints, include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Security Notes

This is a basic implementation designed for educational purposes. The following security considerations are intentionally simplified and can be improved in subsequent lessons:

- Password storage (currently using werkzeug, but can be improved)
- JWT token handling
- Input validation
- SQL injection prevention (SQLAlchemy helps, but can be improved)
- Rate limiting
- CORS configuration
- Error handling and information disclosure

## Database

The application uses SQLite by default. The database file (`events.db`) will be created automatically on first run.

**Note**: The first user registered automatically becomes an admin for demo purposes.



## Running Tests

The tests live in `tests/` and use pytest (already in `requirements.txt`). With the
virtual environment activated, run from the project root:

```bash
python -m pytest
```

Useful options:

```bash
python -m pytest -v                                   # list every test
python -m pytest -rx                                  # show why tests marked xfail fail
python -m pytest tests/test_models.py::TestAuthRoutes # run one test class
python -m pytest -k rsvp                              # run tests whose name matches "rsvp"
```

Each test uses a fresh in-memory SQLite database, so your `instance/events.db` is never
touched and the server doesn't need to be running.

Tests marked `xfail` document known bugs. They show up as `x` in the output and don't
fail the run. Once a bug is fixed, its test passes and pytest fails the run with `[XPASS(strict)]`.
That tells you to remove the `xfail` marker.

## Running with Docker

1. Build the image from the project root:
```bash
docker build -t evently-api .
```

2. Run the container:
```bash
docker run -d --name evently-api -p 5000:5000 evently-api
docker run -d --name evently-api -p 5000:5000 --name banana evently-api
```

The API will be available at `http://localhost:5000` and Swagger UI at `http://localhost:5000/apidocs`.

The image includes a copy of `instance/events.db`, taken at build time. Changes the API makes
are written to the container's copy, so they're lost when you remove the container and don't
show up in your local file. To use your local database instead, mount the `instance/` folder:

```bash
docker run -d --name evently-api -p 5000:5000 -v "${PWD}/instance:/app/instance" evently-api
```

Useful commands:

```bash
docker logs -f evently-api   # follow the server output
docker stop evently-api      # stop the container
docker start evently-api     # start it again (keeps the container's data)
docker rm -f evently-api     # remove the container (its data goes with it)
```


## Publish Docker
```bash 
docker login -u greq # Use Personal Access Token (PAT, best practices)
docker build -t greq/msit-events-api:latest .
docker tag greq/msit-events-api:latest greq/msit-events-api:1.0.0
docker push greq/msit-events-api:latest
```


