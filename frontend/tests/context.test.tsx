import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { it, expect, vi } from 'vitest';
import { ExperimentProvider, useExperiment } from '../src/context/ExperimentContext';
import { report } from './contract';
it('loads real-contract metadata, submits through the API, and publishes the report to consumers', async () => {
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.endsWith('/functions'))
            return new Response(JSON.stringify({ functions: [report.problem] }));
        if (path.endsWith('/algorithms'))
            return new Response(JSON.stringify({ algorithms: [{ identifier: 'gradient_descent', name: 'Gradient Descent', description: 'Test metadata', parameters: { learning_rate: { default: .01, min: 1e-8, max: 10 } } }] }));
        return new Response(JSON.stringify(report), { status: 201 });
    });
    vi.stubGlobal('fetch', fetcher);
    const container = document.createElement('div');
    const root = createRoot(container);
    let shared: ReturnType<typeof useExperiment> | undefined;
    function Consumer() { shared = useExperiment(); return <div>{shared.state.report?.experiment_id || 'empty'}</div>; }
    try {
        await act(async () => root.render(<ExperimentProvider><Consumer /></ExperimentProvider>));
        expect(shared!.state.config?.parameters.gradient_descent.learning_rate).toBe(.01);
        await act(async () => { await shared!.run(); });
        expect(container.textContent).toBe(report.experiment_id);
        expect(shared!.state.frame).toBe(0);
        expect(shared!.state.report?.comparison.winner).toEqual(report.comparison.winner);
        expect(fetcher.mock.calls.some(([url]) => String(url).endsWith('/api/experiments'))).toBe(true);
    }
    finally {
        await act(async () => root.unmount());
        vi.unstubAllGlobals();
    }
});
