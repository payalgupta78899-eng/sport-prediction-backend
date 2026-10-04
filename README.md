# Fantasy Sports Prediction Game — Backend API

Production-ready REST API built with FastAPI, PostgreSQL, Redis, Docker.

## Tech Stack
- **FastAPI** — REST API framework
- **PostgreSQL** — primary database (SQLAlchemy ORM)
- **Redis** — caching, rate limiting, token blacklisting
- **Docker + Nginx** — containerization and reverse proxy
- **JWT** — authentication with httpOnly refresh tokens

## Features
- JWT auth with httpOnly refresh token rotation
- Role Based Access Control (user, moderator, admin)
- Season-based point system with streak bonuses
- Redis leaderboard caching
- Rate limiting per role per minute
- ACID transactions for point awarding
- Audit logging for all important actions
- SELECT FOR UPDATE for race condition prevention

## Quick Start
```bash
docker-compose up --build
```
API available at http://localhost/docs

## API Routes
| Method | Route | Access |
|--------|-------|--------|
| POST | /api/v1/auth/register | Public |
| POST | /api/v1/auth/login | Public |
| POST | /api/v1/auth/refresh | Public |
| POST | /api/v1/auth/logout | Auth |
| GET | /api/v1/seasons/ | Public |
| POST | /api/v1/seasons/ | Admin |
| GET | /api/v1/matches/ | Public |
| POST | /api/v1/matches/ | Moderator |
| PUT | /api/v1/matches/{id}/result | Moderator |
| POST | /api/v1/predictions/ | Auth |
| GET | /api/v1/leaderboard/season/{id} | Public |
| GET | /api/v1/leaderboard/alltime | Public |
| GET | /api/v1/leaderboard/my-stats | Auth |
| GET | /api/v1/admin/users | Admin |
| PUT | /api/v1/admin/users/{id}/ban | Admin |

## Points System
| Action | Points |
|--------|--------|
| Correct prediction | +10 |
| 3 correct in a row | +5 bonus |
| 5 correct in a row | +15 bonus |
| 10 correct in a row | +30 bonus |

Points reset each season. All-time leaderboard sums across seasons.
