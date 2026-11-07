import { z } from 'zod';
import { algorithmSchema, problemSchema, reportSchema, insightSchema, type Request } from '@/types/experiment';
const base = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
export async function fetchValidated<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<T> {
    const timeout = AbortSignal.timeout(180000);
    const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
    let response: Response;
    try {
        response = await fetch(base + path, { ...init, signal, headers: { 'Content-Type': 'application/json', ...init.headers } });
    }
    catch (e) {
        if (init.signal?.aborted)
            throw e;
        throw new Error('Cannot reach the API, or the request timed out. Check the backend URL and server.');
    }
    let data: unknown;
    try {
        data = await response.json();
    }
    catch {
        throw new Error('The API returned malformed JSON.');
    }
    if (!response.ok) {
        const detail = typeof data === 'object' && data !== null && 'detail' in data ? JSON.stringify(data.detail) : response.statusText;
        throw new Error(`API ${response.status}: ${detail}`);
    }
    const parsed = schema.safeParse(data);
    if (!parsed.success)
        throw new Error('Invalid API response: ' + parsed.error.issues.map(i => i.path.join('.') + ': ' + i.message).join('; '));
    return parsed.data;
}
export const api = { functions: (signal?: AbortSignal) => fetchValidated('/api/functions', z.object({ functions: z.array(problemSchema) }), { signal }), algorithms: (signal?: AbortSignal) => fetchValidated('/api/algorithms', z.object({ algorithms: z.array(algorithmSchema) }), { signal }), run: (body: Request, signal?: AbortSignal) => fetchValidated('/api/experiments', reportSchema, { method: 'POST', body: JSON.stringify(body), signal }), report: (id: string, signal?: AbortSignal) => fetchValidated('/api/experiments/' + encodeURIComponent(id), reportSchema, { signal }), insights: (id: string, signal?: AbortSignal) => fetchValidated(`/api/experiments/${encodeURIComponent(id)}/insights`, insightSchema, { method: 'POST', body: JSON.stringify({ force_refresh: true }), signal }) };
