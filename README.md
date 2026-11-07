# Optimisation Arena

Optimisation Arena is an interactive laboratory for comparing numerical
optimisation algorithms. It turns each experiment into observable evidence:
objective-function landscapes, algorithm trajectories, convergence histories,
runtime and evaluation metrics, termination details, and a measured
recommendation.

The project combines a FastAPI service that runs reproducible experiments with
a Next.js dashboard for configuring and exploring the results.

## What it includes

- Benchmark functions including Sphere, Rastrigin, Rosenbrock, and Himmelblau
- Gradient descent, simulated annealing, and genetic algorithm implementations
- Reproducible runs using a configurable random seed
- Side-by-side comparison of up to three algorithms
- Interactive 3D surfaces, contours, heatmaps, paths, and convergence charts
- Configurable bounds, starting points, iterations, landscape resolution,
  repeated trials, evaluation budgets, and ranking metrics
- Result diagnostics covering score, runtime, evaluations, target attainment,
  and termination reason
- Optional AI-generated experiment insights through OpenAI
- FastAPI OpenAPI documentation at `/docs`

## Architecture

```text
backend/    FastAPI API, optimisation algorithms, benchmark functions, reports
frontend/   Next.js dashboard, Plotly visualisations, experiment controls
```

Experiment reports are stored in memory by the backend. They are intended for
interactive sessions and are lost when the backend process restarts.

## Requirements

- Python 3.10+
- Node.js 18+
- npm

## Running locally

Start the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The API starts at `http://localhost:8000`. Check
`http://localhost:8000/api/health` or open the interactive API documentation
at `http://localhost:8000/docs`.

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in a browser. The frontend defaults to
`http://localhost:8000` as its API base URL. To use a different backend,
create `frontend/.env.local` with:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Optional AI insights

AI insights are optional. To enable them, configure the backend environment
before starting the API:

```dotenv
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_INSIGHTS_ENABLED=true
```

Keep API keys in local environment files. Do not commit them to the
repository.

## Useful commands

From `frontend/`:

```bash
npm run lint       # Check frontend code
npm run typecheck  # Run TypeScript checks
npm test           # Run frontend tests
npm run build      # Create a production build
npm start          # Serve the production build
```

From `backend/`, with the virtual environment active:

```bash
pytest
```

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service and AI configuration status |
| `GET` | `/api/functions` | Available benchmark functions |
| `GET` | `/api/algorithms` | Available algorithms and parameters |
| `POST` | `/api/experiments` | Run an experiment and create a report |
| `GET` | `/api/experiments/{id}` | Retrieve a complete report |
| `GET` | `/api/experiments/{id}/summary` | Retrieve a compact summary |
| `GET` | `/api/experiments/{id}/insights` | Retrieve generated insights |
| `POST` | `/api/experiments/{id}/insights` | Generate or refresh insights |

## Interpreting results

Lower objective values are better. A recommendation depends on the selected
ranking metric: best score, runtime, or balanced comparison. Runtime is
machine-dependent, and a single run does not establish algorithm reliability;
use repeated trials when comparing stability.
