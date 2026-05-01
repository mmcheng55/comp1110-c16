# COMP1110 Transport Planner

## Debrief Problem

Hong Kong has many public transport choices, but the best trip is not always the shortest path. A route can be cheaper, faster, more scenic, or require fewer transfers depending on the traveller's priorities. Manually comparing MTR, bus, tram, walking links, fares, transfer points, and travel time is slow and error-prone.

This project builds a desktop transport planning application that lets a user choose an origin and destination, then compares route options using fare, time, scenic score, and transfer information.

## How We Solve It

The application is split into a backend routing service and a frontend desktop GUI.

- The backend stores a transport network as stops and segments, loads the initial network from `backend/network.json`, and exposes REST endpoints for network data and route calculation.
- The routing engine models the network as a graph and uses Dijkstra-based path finding with route diversity logic to return multiple useful alternatives instead of only one path.
- The frontend fetches the network from the backend, displays available stops and route results, and ranks returned routes according to the user's selected preference: cheapest, fastest, most scenic, or balanced.
- Route and fare providers support MTR, bus, and tram data sources, with fallback/local data where needed.

## Technologies Used

- C# / ASP.NET Core Minimal API for the backend service.
- .NET memory cache for route caching.
- Python for the frontend application.
- Tkinter for the desktop GUI.
- Pydantic for typed frontend models and JSON validation.
- Requests for HTTP communication between frontend and backend.
- pytest for frontend tests.
- uv for Python dependency and virtual environment management.

## Required Toolchains / Software

Install these before running the project:

- .NET SDK 10.0 or newer, because `backend/comp1110_backend.csproj` targets `net10.0`.
- Python 3.14 or newer, because `frontend/pyproject.toml` declares `requires-python = ">=3.14"`.
- uv 0.10 or newer for frontend environment setup.
- Tkinter support for your Python installation.
  - macOS python.org installers normally include Tkinter.
  - On Linux, install your distribution's Tk package, for example `python3-tk`. In Ubuntu, you can run `sudo apt-get install python3-tk`.
  - On Windows, the standard Python installer normally includes Tkinter, if didn't, try to reinstall the moduel using the Python Installer via [https://www.python.org/](https://www.python.org/downloads/)

Useful version checks:

```sh
dotnet --version
python --version
uv --version
```

## Project Structure

```text
.
|-- backend/
|   |-- Program.cs
|   |-- Controller.cs
|   |-- View.cs
|   |-- Services/PathFindingService.cs
|   |-- Model/
|   |-- network.json
|   `-- comp1110_backend.csproj
|-- frontend/
|   |-- src/main.py
|   |-- src/controller/
|   |-- src/views/
|   |-- tests/
|   |-- pyproject.toml
|   |-- scripts/setup.sh
|   |-- scripts/setup.bat
|   |-- run_mac.sh
|   `-- run_windows.bat
`-- README.md
```

## Setup Commands

### 1. Clone / Open The Project

Open a terminal at the repository root:

```sh
cd "Code"
```

### 2. Setup Backend

Restore the .NET backend dependencies:

```sh
cd backend
dotnet restore
```

### 3. Setup Frontend

From the frontend folder, use the provided setup script.

macOS / Linux:

```sh
cd ../frontend
chmod +x scripts/setup.sh run_mac.sh
./scripts/setup.sh
```

Windows:

```bat
cd ..\frontend
scripts\setup.bat
```

The setup script runs `uv sync` and writes a `.env` file with:

```text
BACKEND_URL=http://localhost:5117
```

## How To Run The Code

Run the backend and frontend in two separate terminals.

### Terminal 1: Start Backend

```sh
cd backend
dotnet run --launch-profile http
```

The backend should listen on:

```text
http://localhost:5117
```

Quick backend checks:

```sh
curl http://localhost:5117/
curl http://localhost:5117/network
curl "http://localhost:5117/route?start=HKU&end=Central"
```

### Terminal 2: Start Frontend

macOS / Linux:

```sh
cd frontend
./run_mac.sh
```

Or manually:

```sh
cd frontend
source .venv/bin/activate
python src/main.py
```

Windows:

```bat
cd frontend
run_windows.bat
```

Or manually:

```bat
cd frontend
.venv\Scripts\activate
python src\main.py
```

Do not run individual files inside `frontend/src/views/` directly. The correct frontend entry point is `frontend/src/main.py`.

## Running Tests

Frontend tests:

```sh
cd frontend
uv run pytest
```

Backend build check:

```sh
cd backend
dotnet build
```

## Backend API Summary

- `GET /` returns a simple health message.
- `GET /network` returns the loaded transport network.
- `POST /network/set` replaces the active transport network and writes it to `backend/network.json`.
- `GET /route?start=<stop>&end=<stop>` returns possible routes between two stop names.

## Notes

- The frontend defaults to `http://localhost:5117`; edit `frontend/.env` if the backend runs on another URL.
- If the frontend opens but the stop list is empty, start the backend first and confirm `/network` returns data.
- The backend expects to run from the `backend/` directory so that `network.json` resolves correctly.
