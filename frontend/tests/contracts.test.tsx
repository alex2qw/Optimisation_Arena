import { describe, it, expect, vi, afterEach } from 'vitest';
import { z } from 'zod';
import { fetchValidated, api } from '../src/lib/api';
import { convergence, frames, pathAt, winnerName } from '../src/lib/adapters';
import { reportSchema, requestSchema } from '../src/types/experiment';
import { initial, reducer } from '../src/context/ExperimentContext';
import { report, request } from './contract';
import { readFileSync, existsSync } from 'node:fs';
afterEach(() => vi.unstubAllGlobals());
describe('API boundary', () => {
    it('validates successful responses', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"ok":true}'))); expect(await fetchValidated('/test', z.object({ ok: z.boolean() }))).toEqual({ ok: true }); });
    it.each([422, 404, 500])('preserves useful HTTP %s errors', async (status) => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"request rejected"}', { status }))); await expect(fetchValidated('/test', z.unknown())).rejects.toThrow(`API ${status}`); });
    it('rejects malformed JSON', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not json'))); await expect(fetchValidated('/test', z.unknown())).rejects.toThrow('malformed JSON'); });
    it('rejects invalid response schemas', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}'))); await expect(fetchValidated('/test', z.object({ value: z.number() }))).rejects.toThrow('Invalid API response'); });
    it('explains connection failure', async () => { vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network'))); await expect(fetchValidated('/test', z.unknown())).rejects.toThrow('Cannot reach the API'); });
    it('posts the real request shape', async () => { const f = vi.fn().mockResolvedValue(new Response(JSON.stringify(report))); vi.stubGlobal('fetch', f); await api.run(request); expect(f.mock.calls[0][0]).toMatch(/\/api\/experiments$/); expect(JSON.parse(f.mock.calls[0][1].body)).toEqual(request); });
});
describe('report adapters', () => {
    it('validates report and preserves grid orientation z[y][x]', () => { const r = reportSchema.parse(report); expect(r.landscape.surface.z[1][0]).toBe(4); expect(r.landscape.surface.z[0][1]).toBe(1); });
    it('rejects inconsistent dimensions', () => { const r = structuredClone(report); r.landscape.surface.z[0] = [0]; expect(reportSchema.safeParse(r).success).toBe(false); });
    it('pairs recorded position and current score, clamps short histories', () => { expect(pathAt(report, 'gradient_descent', 99)).toEqual([{ x: 1, y: 1, z: 2, best: 2, iteration: 0 }, { x: .5, y: .5, z: .5, best: .5, iteration: 1 }]); expect(frames(report)).toBe(1); expect(pathAt(report, 'missing', 0)).toEqual([]); });
    it('rejects misaligned trajectories and convergence', () => { const r = structuredClone(report); r.animation.algorithms.gradient_descent.scores.pop(); expect(reportSchema.safeParse(r).success).toBe(false); const c = structuredClone(report); c.convergence.series[0].best_so_far.pop(); expect(reportSchema.safeParse(c).success).toBe(false); });
    it('maps both convergence axes without synthesising values', () => { expect(convergence(report, 'function_evaluations')[0]).toMatchObject({ x: [1, 3], y: [2, .5] }); expect(convergence(report, 'iterations')[0].x).toEqual([0, 1]); });
    it('uses the backend winner and does not invent one', () => { expect(winnerName(report)).toBe('Gradient Descent'); expect(winnerName({ ...report, comparison: { ...report.comparison, winner: null } })).toBeUndefined(); });
    it('accepts missing optional metrics and null AI', () => { expect(reportSchema.parse(report).results[0].runtime_ms).toBeUndefined(); expect(reportSchema.parse(report).ai_insights).toBeNull(); });
    it('replaces all report panels and resets playback atomically', () => { const result = reducer({ ...initial, playing: true, frame: 20, busy: true }, { type: 'report', report }); expect(result.report).toBe(report); expect(result.frame).toBe(0); expect(result.playing).toBe(false); expect(result.busy).toBe(false); expect(result.history[0].id).toBe(report.experiment_id); });
});
describe('form contract', () => {
    it('constructs a valid backend payload', () => expect(requestSchema.parse(request)).toEqual(request));
    it('rejects empty selection, invalid budgets, bounds and starts', () => { for (const value of [{ ...request, algorithms: [] }, { ...request, iterations: 0 }, { ...request, bounds: { x: [2, -2], y: [-2, 2] } }, { ...request, starting_point: [9, 9] }, { ...request, seed: NaN }])
        expect(requestSchema.safeParse(value).success).toBe(false); });
    it('rejects elite count exceeding population', () => expect(requestSchema.safeParse({ ...request, parameters: { genetic_algorithm: { population_size: 4, elite_count: 4 } } }).success).toBe(false));
});
const fixture = new URL('./fixtures/real-report.json', import.meta.url);
it.skipIf(!existsSync(fixture))('validates captured REAL backend report', () => { const r = reportSchema.parse(JSON.parse(readFileSync(fixture, 'utf8'))); for (const row of r.results) {
    const p = pathAt(r, row.algorithm, Number.MAX_SAFE_INTEGER);
    expect(p.length).toBe(r.animation.algorithms[row.algorithm].path.length);
} expect(r.landscape.surface.z.length).toBe(r.landscape.surface.y.length); });
