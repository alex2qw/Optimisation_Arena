import type {Data} from 'plotly.js';
import type {Report} from '@/types/experiment';
import {color, fmt} from './adapters';

export const TRAIL_STEPS = 24;
const TRAIL_BANDS = 8;
export type ReplayTrace = Data & {mode: 'lines' | 'markers'; x: number[]; y: number[]; z?: number[]; opacity?: number};

// Frames are record indices, not elapsed time or a shared iteration budget.
export function replayAt(report: Report, id: string, frame: number) {
  const trajectory = report.animation.algorithms[id];
  if (!trajectory?.path.length) return null;
  const index = Math.max(0, Math.min(Math.floor(frame), trajectory.path.length - 1));
  const position = trajectory.path[index];
  const bestPosition = trajectory.best_so_far_positions?.[index];
  return {
    index, x: position[0], y: position[1], score: trajectory.scores[index],
    bestScore: trajectory.best_so_far[index], bestPosition,
    iteration: trajectory.iterations[index], evaluations: trajectory.function_evaluations[index],
    finished: index === trajectory.path.length - 1,
  };
}

export function convergenceAt(report: Report, frame: number, axis: 'iterations' | 'function_evaluations') {
  return report.convergence.series.flatMap(series => {
    if (!series.best_so_far.length) return [];
    const index = Math.max(0, Math.min(Math.floor(frame), series.best_so_far.length - 1));
    return [{id: series.algorithm, name: series.display_name, x: series[axis][index], y: series.best_so_far[index]}];
  });
}

export function replayTraces(report: Report, frame: number, three: boolean, fadeTrails = true): ReplayTrace[] {
  const traces: ReplayTrace[] = [];
  for (const result of report.results) {
    const id = result.algorithm;
    const current = replayAt(report, id, frame);
    if (!current) continue;
    const trajectory = report.animation.algorithms[id];
    const type = three ? 'scatter3d' : 'scatter';
    const common = {type, legendgroup: id, showlegend: false};
    if (!fadeTrails && current.index > 0) {
      const points = trajectory.path.slice(0, current.index + 1);
      traces.push({
        ...common, name: `${result.display_name} recorded path`, mode: 'lines',
        x: points.map(p => p[0]), y: points.map(p => p[1]),
        ...(three ? {z: trajectory.scores.slice(0, current.index + 1)} : {}),
        line: {color: color(id), width: three ? 5 : 3}, opacity: 1, hoverinfo: 'skip',
      } as ReplayTrace);
    } else if (fadeTrails) {
      const start = Math.max(0, current.index - TRAIL_STEPS);
      const bandSize = Math.ceil(TRAIL_STEPS / TRAIL_BANDS);
      // Adjacent slices share their boundary point: fading never invents a coordinate.
      for (let band = 0; band < TRAIL_BANDS; band++) {
        const end = current.index - band * bandSize;
        const begin = Math.max(start, end - bandSize);
        if (end <= start) break;
        const points = trajectory.path.slice(begin, end + 1);
        traces.push({
          ...common, name: `${result.display_name} recent path`, mode: 'lines',
          x: points.map(p => p[0]), y: points.map(p => p[1]),
          ...(three ? {z: trajectory.scores.slice(begin, end + 1)} : {}),
          line: {color: color(id), width: three ? 5 : 3},
          opacity: 0.9 - band * 0.1, hoverinfo: 'skip',
        } as ReplayTrace);
      }
    }
    traces.push({
      ...common, name: `${result.display_name} current candidate`, showlegend: true, mode: 'markers',
      x: [current.x], y: [current.y], ...(three ? {z: [current.score]} : {}),
      marker: {color: color(id), size: three ? 7 : 11, symbol: 'circle', line: {color: '#ffffff', width: 2}},
      text: [`${result.display_name} · current candidate<br>Iteration ${current.iteration} · f = ${fmt(current.score)}`],
      hovertemplate: '%{text}<extra></extra>',
    } as ReplayTrace);
    // Older reports may omit best positions. Never substitute a future final result.
    if (current.bestPosition) {
      traces.push({
        ...common, name: `${result.display_name} best discovery`, mode: 'markers',
        x: [current.bestPosition[0]], y: [current.bestPosition[1]],
        ...(three ? {z: [current.bestScore]} : {}),
        marker: {color: color(id), size: three ? 5 : 9, symbol: 'diamond', line: {color: '#ffffff', width: 1}},
        text: [`${result.display_name} · best discovery so far<br>f = ${fmt(current.bestScore)}`],
        hovertemplate: '%{text}<extra></extra>',
      } as ReplayTrace);
    }
  }
  return traces;
}
