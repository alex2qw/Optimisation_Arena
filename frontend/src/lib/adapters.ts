import type { Report } from '@/types/experiment';
export const colors: Record<string, string> = { gradient_descent: '#ff525e', simulated_annealing: '#fbbf24', genetic_algorithm: '#30df9a' };
export const color = (id: string) => colors[id] || '#9c88ff';
export function frames(r: Report) { return Math.max(0, ...Object.values(r.animation.algorithms).map(t => t.path.length - 1)); }
export function pathAt(r: Report, id: string, frame: number) { const t = r.animation.algorithms[id]; if (!t)
    return []; return t.path.slice(0, frame + 1).map((p, i) => ({ x: p[0], y: p[1], z: t.scores[i], best: t.best_so_far[i], iteration: t.iterations[i] })); }
export const convergence = (r: Report, axis: 'iterations' | 'function_evaluations') => r.convergence.series.map(s => ({ id: s.algorithm, name: s.display_name, x: s[axis], y: s.best_so_far }));
export const winnerName = (r: Report) => r.results.find(x => x.algorithm === r.comparison.winner?.algorithm)?.display_name ?? r.comparison.winner?.algorithm;
export const fmt = (v: number | null | undefined) => v == null ? 'Unavailable' : Math.abs(v) > 0 && (Math.abs(v) < .001 || Math.abs(v) > 1e6) ? v.toExponential(3) : v.toLocaleString(undefined, { maximumFractionDigits: 4 });
