# Restaurant HQ Backend

A complete, reusable **FastAPI + MongoDB** authentication and authorization template.

## Features
- **FastAPI** for high-performance async API.
- **MongoDB (Motor)** for asynchronous database interaction.
- **JWT (Access + Refresh tokens)** for secure, stateless auth.
- **Bcrypt** for password hashing.
- **Role-Based Access Control (RBAC)**: `student`, `academy_admin`, `super_admin`.
- **CORS** pre-configured for React/Vite development.
- **Modular Structure** (config, db, auth, models, routers).

## Setup
1. Clone the project.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file (see `.env.example`):
   ```
   SECRET_KEY=
   ALGORITHM=
   ACCESS_TOKEN_MINUTES=30
   REFRESH_TOKEN_DAYS=7
   MONGODB_URL=
   ```

## API Endpoints
- `POST /auth/register` - Create user
- `POST /auth/login` - Receive tokens
- `POST /auth/refresh` - Get new access token
- `GET /users/me` - Own profile
- `GET /users/` - List all users (admin only)

## How to Run
```bash
uvicorn main:app --reload
```
Docs available at `http://127.0.0.1:8000/docs`
