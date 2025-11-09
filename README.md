# Nexa

Gen-AI for Organizations. Streamline all workflows across messenger, workspaces, and organizational systems in one place, and make them smart using AI.

## What is this?

This is the source code of old Nexa codebase's latest version.

This codebase is not now active in the Nexa AI and is under MIT Open Source License, feel free to use the codebase.

---

## Project Overview

This project provides a full-stack solution to improve organizational productivity using AI-driven automation and integration. It includes:

- **FastAPI backend API** (`/api` folder)  
- **Next.js frontend web app** (`/web` folder)  
- **Automated tests** (`/tests` folder)

The backend handles authentication, user management, invitations, organizations, and AI-driven workflows. The frontend provides an interactive interface for users.

---

## Features

- User authentication and authorization with roles (sysadmin, orgadmin, orguser)  
- Invitation system with secure invite codes and approval workflow  
- Organization and user management APIs  
- Swagger UI with direct login and token input support  
- Dockerized for easy deployment  
- Environment variable configuration via `.env`  

---

## Project Structure

```text
/
├── api/               # FastAPI backend API source code
├── web/               # Next.js frontend web app source code
├── tests/             # Automated test cases
├── Dockerfile         # Dockerfile to build backend container
├── docker-compose.yml # Docker Compose config to run the whole stack
├── .env.example       # Example environment variables config
└── README.md          # This documentation
```
---

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- An `.env` file created based on `.env.example` with your environment variables, including keys like:

```env
SYSADMIN_USERNAME=admin
SYSADMIN_PASSWORD=changeme
RESEND_API_KEY=your_resend_api_key
```

### Running the Project with Docker

Build and start the containers using Docker Compose:

```bash
docker-compose up --build
```

This will start the FastAPI backend and the Next.js frontend, exposing their respective ports.

Accessing the API and Frontend (In the default configuration)
	•	API Swagger UI: http://localhost:8000/docs
	•	Frontend app: http://localhost

### Running Tests

Make sure you have your Python environment ready with dependencies installed.

Run the tests using:

```bash
PYTHONPATH=. pytest
```

Tests are located in the /tests directory.