'use client';

import {createContext, useContext, useEffect, useReducer, useRef, useCallback, type ReactNode} from 'react';
import {api} from '@/lib/api';
import {frames} from '@/lib/adapters';
import {requestSchema, type Algorithm, type Problem, type Report, type Request, type View} from '@/types/experiment';

export type State = {
  functions: Problem[];
  algorithms: Algorithm[];
  config: Request | null;
  report: Report | null;
  loading: boolean;
  busy: boolean;
  error: string;
  insightBusy: boolean;
  view: View;
  map: string;
  paths: boolean;
  fadeTrails: boolean;
  starts: boolean;
  minima: boolean;
  frame: number;
  playing: boolean;
  speed: number;
  history: {id: string; name: string}[];
};

export const initial: State = {
  functions: [], algorithms: [], config: null, report: null,
  loading: true, busy: false, error: '', insightBusy: false,
  view: 'surface', map: 'Viridis', paths: true, fadeTrails: true, starts: true, minima: true,
  frame: 0, playing: false, speed: 1, history: [],
};
export type Action = {type: 'patch'; value: Partial<State>} | {type: 'report'; report: Report};

export function reducer(state: State, action: Action): State {
  if (action.type === 'patch') return {...state, ...action.value};
  return {
    ...state, report: action.report, busy: false, error: '', frame: 0, playing: false,
    history: [
      {id: action.report.experiment_id, name: action.report.problem.name},
      ...state.history.filter(item => item.id !== action.report.experiment_id),
    ],
  };
}

const Context = createContext<{
  state: State;
  patch: (value: Partial<State>) => void;
  configure: (value: Partial<Request>) => void;
  select: (id: string) => void;
  run: () => Promise<void>;
  load: (id: string) => Promise<void>;
  insights: () => Promise<void>;
  retry: () => void;
} | null>(null);

export function ExperimentProvider({children}: {children: ReactNode}) {
  const [state, dispatch] = useReducer(reducer, initial);
  const active = useRef<AbortController | null>(null);
  const insightRequest = useRef<AbortController | null>(null);
  const catalogRequest = useRef<AbortController | null>(null);
  const patch = useCallback((value: Partial<State>) => dispatch({type: 'patch', value}), []);

  const metadata = useCallback(() => {
    catalogRequest.current?.abort();
    const controller = new AbortController();
    catalogRequest.current = controller;
    patch({loading: true, error: ''});
    Promise.all([api.functions(controller.signal), api.algorithms(controller.signal)])
      .then(([functions, algorithms]) => {
        if (controller.signal.aborted) return;
        const problem = functions.functions.find(item => item.identifier === 'rastrigin') || functions.functions[0];
        if (!problem) throw new Error('No functions are available.');
        patch({
          functions: functions.functions, algorithms: algorithms.algorithms, loading: false,
          config: {
            function: problem.identifier, algorithms: algorithms.algorithms.map(item => item.identifier),
            iterations: 500, seed: 42, bounds: problem.bounds,
            parameters: Object.fromEntries(algorithms.algorithms.map(item => [
              item.identifier, Object.fromEntries(Object.entries(item.parameters).map(([key, value]) => [key, value.default])),
            ])),
            landscape: {resolution: 80}, comparison: {ranking_metric: 'best_score'},
            repeated_trials: 1, max_evaluations: 100000,
          },
        });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) patch({error: error instanceof Error ? error.message : String(error), loading: false});
      });
  }, [patch]);

  useEffect(() => {
    metadata();
    return () => {
      catalogRequest.current?.abort();
      active.current?.abort();
      insightRequest.current?.abort();
    };
  }, [metadata]);

  useEffect(() => {
    if (!state.playing || !state.report) return;
    const max = frames(state.report);
    const timer = setTimeout(() => {
      if (state.frame >= max) patch({playing: false});
      else patch({frame: state.frame + 1});
    }, Math.max(16, 100 / state.speed));
    return () => clearTimeout(timer);
  }, [state.playing, state.frame, state.report, state.speed, patch]);

  function configure(value: Partial<Request>) {
    if (state.config) patch({config: {...state.config, ...value}});
  }

  async function execute(operation: (signal: AbortSignal) => Promise<Report>) {
    active.current?.abort();
    insightRequest.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    patch({busy: true, error: '', playing: false, insightBusy: false});
    try {
      const report = await operation(controller.signal);
      if (!controller.signal.aborted) dispatch({type: 'report', report});
    } catch (error) {
      if (!controller.signal.aborted) patch({busy: false, error: error instanceof Error ? error.message : String(error)});
    }
  }

  async function run() {
    try {
      // The backend rejects parameter sets for algorithms not selected in this run.
      const config = requestSchema.parse({
        ...state.config,
        parameters: Object.fromEntries(Object.entries(state.config?.parameters || {})
          .filter(([id]) => state.config?.algorithms.includes(id))),
      });
      await execute(signal => api.run(config, signal));
    } catch (error) {
      patch({error: error instanceof Error ? error.message : String(error)});
    }
  }

  async function insights() {
    if (!state.report) return;
    const report = state.report;
    insightRequest.current?.abort();
    const controller = new AbortController();
    insightRequest.current = controller;
    patch({insightBusy: true, error: ''});
    try {
      const result = await api.insights(report.experiment_id, controller.signal);
      if (!controller.signal.aborted) patch({report: {...report, ai_insights: result}, insightBusy: false});
    } catch (error) {
      if (!controller.signal.aborted) patch({insightBusy: false, error: error instanceof Error ? error.message : String(error)});
    }
  }

  function select(id: string) {
    const problem = state.functions.find(item => item.identifier === id);
    if (problem) configure({function: id, bounds: problem.bounds, starting_point: undefined});
  }

  return <Context.Provider value={{state, patch, configure, select, run,
    load: id => execute(signal => api.report(id, signal)), insights, retry: metadata}}>
    {children}
  </Context.Provider>;
}

export function useExperiment() {
  const context = useContext(Context);
  if (!context) throw new Error('ExperimentProvider is required');
  return context;
}
