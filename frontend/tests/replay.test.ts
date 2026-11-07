import {describe, expect, it} from 'vitest';
import {replayAt, replayTraces, convergenceAt, TRAIL_STEPS} from '../src/lib/replay';
import {report} from './contract';
import {reportSchema} from '../src/types/experiment';

function example() {
  const r = structuredClone(report);
  const t = r.animation.algorithms.gradient_descent;
  // Current candidate worsens; best recorded position stays at the earlier discovery.
  t.path = [[1, 1], [.5, .5], [1, 0]];
  t.scores = [2, .5, 1];
  t.best_so_far = [2, .5, .5];
  t.best_so_far_positions = [[1, 1], [.5, .5], [.5, .5]];
  t.iterations = [0, 2, 4];
  t.function_evaluations = [1, 4, 7];
  r.convergence.series[0] = {...r.convergence.series[0], best_so_far: t.best_so_far,
    iterations: t.iterations, function_evaluations: t.function_evaluations};
  return r;
}

describe('recorded-search replay', () => {
  it('preserves and validates best-position history from the backend', () => {
    const r = example();
    expect(reportSchema.parse(r).animation.algorithms.gradient_descent.best_so_far_positions).toEqual([[1,1],[.5,.5],[.5,.5]]);
    r.animation.algorithms.gradient_descent.best_so_far_positions!.pop();
    expect(reportSchema.safeParse(r).success).toBe(false);
  });
  it('keeps the current candidate separate from its earlier best discovery', () => {
    expect(replayAt(example(), 'gradient_descent', 2)).toMatchObject({x: 1, y: 0, score: 1, bestScore: .5, bestPosition: [.5,.5], iteration: 4});
    const traces = replayTraces(example(), 2, true);
    const head = traces.find(t => t.name?.endsWith('current candidate'));
    const best = traces.find(t => t.name?.endsWith('best discovery'));
    expect(head).toMatchObject({x:[1],y:[0],z:[1]});
    expect(best).toMatchObject({x:[.5],y:[.5],z:[.5]});
  });
  it('scrubs backwards without exposing later states and clamps shorter histories', () => {
    expect(replayAt(example(), 'gradient_descent', 0)).toMatchObject({score:2,bestScore:2,bestPosition:[1,1]});
    expect(replayAt(example(), 'gradient_descent', 900)).toEqual(replayAt(example(), 'gradient_descent', 2));
    expect(replayAt(example(), 'gradient_descent', -1)).toEqual(replayAt(example(), 'gradient_descent', 0));
  });
  it('does not substitute the final best position when the history is missing', () => {
    expect(replayAt(report, 'gradient_descent', 0)?.bestPosition).toBeUndefined();
    expect(replayTraces(report, 0, false).some(t => t.name?.endsWith('best discovery'))).toBe(false);
  });
  it('synchronises convergence cursors to actual iterations and evaluations', () => {
    expect(convergenceAt(example(), 1, 'iterations')[0]).toMatchObject({x:2,y:.5});
    expect(convergenceAt(example(), 1, 'function_evaluations')[0]).toMatchObject({x:4,y:.5});
    expect(convergenceAt(example(), 99, 'function_evaluations')[0]).toMatchObject({x:7,y:.5});
  });
  it('shows only a bounded recent trail with older segments less opaque', () => {
    const r = example(); const t = r.animation.algorithms.gradient_descent;
    t.path = Array.from({length:60}, (_,i) => [i,0] as [number,number]);
    t.scores = Array.from({length:60}, (_,i) => i);
    const traces = replayTraces(r, 50, false).filter(t => t.mode === 'lines');
    expect(traces.length).toBe(8);
    expect(traces[0].opacity).toBeGreaterThan(traces.at(-1)!.opacity!);
    const coordinates = traces.flatMap(t => Array.from(t.x as number[]));
    expect(Math.min(...coordinates)).toBe(50-TRAIL_STEPS);
    expect(Math.max(...coordinates)).toBe(50);
  });
  it('handles frame zero and absent histories without invented paths', () => {
    expect(replayTraces(example(), 0, true).filter(t=>t.mode==='lines')).toEqual([]);
    const r = example(); r.animation.algorithms = {};
    expect(replayAt(r,'gradient_descent',0)).toBeNull();
    expect(replayTraces(r,10,true)).toEqual([]);
  });
});
