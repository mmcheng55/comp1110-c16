# Transport Planning Frontend

A desktop graphical user interface (GUI) for a transport planning application built with Python and Tkinter. This application allows users to view a transit network, pull live data from open APIs (e.g., MTR), and calculate the best routes between stops based on personal preferences like cost, time, and scenic score.

## Architecture

The project follows a modular Model-View-Controller (MVC) architecture to separate concerns:

- **Models (`src/models.py`)**: Pydantic models for type-safe representations of the domain entities (`Stop`, `Segment`, `Route`, `TransportNetwork`).
- **Views (`src/views/`)**: Tkinter-based user interfaces.
  - `routing_page.py`: The home page to select routes and scoring preferences.
  - `route_ranking_page.py`: The results page showing ranked routes.
  - `components/`: Reusable UI elements, such as `RouteCard` for summaries and `NetworkView` for an interactive map.
  - `navigator.py`: Manages transitioning and routing between the various views.
- **Controllers (`src/controller/`)**: Core logic to handle data processing and backend communication.
  - `network_controller.py`: Fetches and caches the available transit stops and connections.
  - `route_controller.py`: Sends routing queries and scores the retrieved paths.
  - `mtr_controller.py`: Imports and parses real-world MTR data from CSV feeds.

## Running the frontend

This project should be started from the project root using the app entry point:

`src/main.py`

Do **not** run `src/views/main_view.py` directly. It is only one view module, and running it by itself causes import errors such as:

`ModuleNotFoundError: No module named 'controller'`

That error does **not** mean you need to install a package called `controller`. It means Python was started from the wrong file, so the `src` folder was not treated as the import root.

## Windows

From the project root:

```bat
.venv\Scripts\activate
python src\main.py
```

Or use the provided launcher:

```bat
run_windows.bat
```

## macOS / Linux

From the project root:

```sh
source .venv/bin/activate
python src/main.py
```

Or use the provided launcher:

```sh
./run_mac.sh
```

## First-time setup

If the virtual environment does not exist yet, run:

### Windows
```bat
scripts\setup.bat
```

### macOS / Linux
```sh
./scripts/setup.sh
```

This uses `uv sync` to create the environment and install dependencies.

## Backend requirement

The UI fetches data from a backend server using `BACKEND_URL`, which defaults to:

`http://localhost:5117`

If the frontend opens but the stop list is empty, the backend is probably not running.
