"""Capture a real report from the running backend; no fabricated fallback."""
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

base = os.environ.get('API_BASE_URL', 'http://localhost:8000').rstrip('/')


def get(path):
    with urlopen(base + path, timeout=180) as response:
        return json.load(response)


try:
    assert get('/api/health')['status'] == 'ok'
    assert get('/api/functions')['functions']
    assert get('/api/algorithms')['algorithms']
    payload = {
        'function': 'rastrigin',
        'algorithms': ['gradient_descent', 'simulated_annealing', 'genetic_algorithm'],
        'iterations': 40, 'seed': 42, 'starting_point': [3.5, -2.5],
        'landscape': {'resolution': 20},
    }
    request = Request(base + '/api/experiments', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=180) as response:
        report = json.load(response)
    route = '/api/experiments/' + report['experiment_id']
    assert get(route)['experiment_id'] == report['experiment_id']
    assert get(route + '/summary')['winner'] == report['comparison']['winner']
    assert get(route + '/insights')['status'] == report['ai_insights']['status']
except URLError as error:
    raise SystemExit(f'Real backend integration failed at {base}: {error}') from error

path = Path(__file__).resolve().parent.parent / 'tests/fixtures/real-report.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2) + '\n')
print(f'Captured real report {report["experiment_id"]} at {path}')
