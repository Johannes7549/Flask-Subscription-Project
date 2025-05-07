# Subscription API

A Flask-based REST API for managing user subscriptions and subscription plans, with robust Docker/MySQL support and production-ready features.

## Features

- User registration and JWT authentication
- Admin user auto-creation via environment variables and init script
- Subscription plan management (CRUD, admin-only)
- Plan types: `free`, `basic`, `pro` (filterable)
- Users can have multiple subscriptions (one per plan type)
- Subscribe, upgrade, and cancel subscriptions per plan
- Optimized queries for active subscriptions and history (with raw SQL where needed)
- Indexes for performance on key columns
- Filter plans and history by type
- MySQL database with SQLAlchemy ORM
- Dockerized setup for easy deployment

## Prerequisites

- Python 3.8+
- MySQL 8.0+
- Docker and Docker Compose (for containerized deployment)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd subscription-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Admin User Creation

On container startup, an admin user is created automatically using environment variables. Set the following in your `.env` file:

```
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=yourpassword
```

The `init_admin.py` script will create the admin user after migrations are applied. If the user already exists, it will be skipped.

## Running the Application

### Development Mode

1. Start the MySQL database:
```bash
docker-compose up -d db
```

2. Run database migrations:
```bash
flask db upgrade
```

3. Create the admin user:
```bash
python init_admin.py
```

4. Run the Flask application:
```bash
flask run
```

### Production Mode

1. Build and start all services:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:5000`.

**Note:** The web service waits for MySQL to be ready before running migrations and the admin script.

## API Endpoints

### Authentication
- `POST /api/auth/register`  
  Register a new user.  
  **Body:** `{ "email": "user@example.com", "password": "..." }`
- `POST /api/auth/login`  
  Login and get JWT token.  
  **Body:** `{ "email": "user@example.com", "password": "..." }`

### Subscription Plans (Admin Only)
- `POST /api/subscriptions/plans`  
  Create a new subscription plan.  
  **Body:** `{ "name": "Pro", "type": "pro", "price": 20.0 }`
- `GET /api/subscriptions/plans`  
  List all subscription plans.  
  **Query params:** `?type=pro` (optional, filter by type)
- `GET /api/subscriptions/plans/<id>`  
  Get plan details by ID.
- `PUT /api/subscriptions/plans/<id>`  
  Update a plan (admin only).
- `DELETE /api/subscriptions/plans/<id>`  
  Delete a plan (admin only).

### User Subscriptions
- `POST /api/subscriptions/subscribe`  
  Subscribe to a plan.  
  **Body:** `{ "plan_id": 1 }`  
  (Only one active subscription per plan type per user)
- `POST /api/subscriptions/upgrade`  
  Upgrade a subscription for a specific plan.  
  **Body:** `{ "subscription_id": 1, "new_plan_id": 2 }`
- `POST /api/subscriptions/cancel`  
  Cancel a subscription.  
  **Body:** `{ "subscription_id": 1 }`
- `GET /api/subscriptions/my-subscriptions`  
  Get all active subscriptions for the authenticated user.
- `GET /api/subscriptions/history`  
  Get subscription history for the user.  
  **Query params:** `?type=basic` (optional, filter by plan type)

## Database Migrations

To create a new migration:
```bash
flask db migrate -m "Description of changes"
```

To apply migrations:
```bash
flask db upgrade
```

## Optimizations & Indexes

- Key columns (user_id, plan_id, type) are indexed for performance.
- Some endpoints use raw SQL for optimized queries (see code for details).
- Alembic is used for migrations; handle foreign key constraints carefully when downgrading.

## Datetime Handling

- All datetimes are stored in UTC (naive in MySQL).
- The API handles naive/aware datetime comparisons to avoid errors.

## Dockerized Setup & MySQL Readiness

- The `docker-compose.yml` ensures MySQL is ready before running migrations and the admin script.
- If you encounter connection errors, try restarting the web service after the db is healthy:
  ```bash
  docker-compose restart web
  ```

## Troubleshooting

- **MySQL not ready:** Wait for the db container to be healthy before starting the web service.
- **Alembic downgrade errors:** May require manual table drops due to foreign key constraints.
- **Datetime errors:** Ensure your system timezone is set correctly; the API expects UTC.
- **Admin not created:** Ensure environment variables are set and migrations have run before the admin script.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 