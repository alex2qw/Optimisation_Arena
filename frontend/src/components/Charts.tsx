'use client';
import dynamic from 'next/dynamic';
import { useMemo, useRef, useState } from 'react';
import type { Data, Layout, PlotlyHTMLElement } from 'plotly.js';
import { Download, Maximize, Pause, Play, RotateCcw } from 'lucide-react';
import { useExperiment } from '@/context/ExperimentContext';
import { color, convergence, fmt, frames } from '@/lib/adapters';
import {convergenceAt, replayAt, replayTraces, TRAIL_STEPS} from '@/lib/replay';
import type { View } from '@/types/experiment';
const Plot = dynamic(() => import('./Plot'), { ssr: false, loading: () => <div className="empty">Loading scientific visualisation…</div> });
export const views: {
    id: View;
    label: string;
}[] = [{ id: 'surface', label: '3D Surface' }, { id: 'contour', label: 'Contour Plot (2D)' }, { id: 'paths', label: 'Algorithm Paths Only' }, { id: 'heatmap', label: 'Heatmap' }];
const axis = { gridcolor: '#1c334b', zerolinecolor: '#36506d', color: '#98afca', title: { text: 'x' } };
const baseLayout: Partial<Layout> = { paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#b6c9e2', family: 'Arial, sans-serif', size: 11 }, margin: { l: 48, r: 20, t: 16, b: 48 }, autosize: true, legend: { orientation: 'h', x: 0, y: 1.09, font: { size: 10 } }, xaxis: axis, yaxis: { ...axis, title: { text: 'y' } } };
export function Landscape() {
    const { state: s, patch } = useExperiment();
    const [camera, setCamera] = useState(0);
    const [chartError, setChartError] = useState<{key: string; message: string} | null>(null);
    const container = useRef<HTMLDivElement>(null);
    const graph = useRef<PlotlyHTMLElement | null>(null);
    const r = s.report;
    const surface = useMemo<Data[]>(() => { if (!r || s.view === 'paths')
        return []; const grid = r.landscape.surface; if (!grid.x.length || !grid.y.length)
        return []; return [{ type: s.view === 'surface' ? 'surface' : s.view === 'contour' ? 'contour' : 'heatmap', x: grid.x, y: grid.y, z: grid.z, colorscale: s.map, showscale: false, hovertemplate: 'x: %{x:.3f}<br>y: %{y:.3f}<br>f: %{z:.5g}<extra></extra>', ...(s.view === 'surface' ? { opacity: .88 } : {}) } as Data]; }, [r, s.view, s.map]);
    const data = useMemo<Data[]>(() => {
        if (!r)
            return [];
        const three = s.view === 'surface';
        const traces: Data[] = [...surface];
        if (s.paths) traces.push(...replayTraces(r, s.frame, three, s.fadeTrails));
        if (s.starts) for (const row of r.results) {
            const trajectory = r.animation.algorithms[row.algorithm];
            const point = trajectory?.path[0];
            if (!point) continue;
            traces.push({name: `${row.display_name} start`, type: three ? 'scatter3d' : 'scatter',
                mode: 'markers', x: [point[0]], y: [point[1]], ...(three ? {z: [trajectory.scores[0]]} : {}),
                marker: {color: '#eef4ff', size: three ? 4 : 7, symbol: three ? 'square' : 'square-open'},
                showlegend: false, hovertemplate: `${row.display_name} start (%{x}, %{y})<extra></extra>`,
            } as Data);
        }
        if (s.minima && r.landscape.known_optima.length) {
            const o = r.landscape.known_optima;
            traces.push({ name: 'Known global minima', type: three ? 'scatter3d' : 'scatter', mode: 'markers', x: o.map(a => a.position[0]), y: o.map(a => a.position[1]), ...(three ? { z: o.map(a => a.objective_value) } : {}), marker: { color: '#ff6ba0', size: three ? 7 : 13, symbol: three ? 'diamond' : 'star' }, hovertemplate: 'Known minimum (%{x}, %{y})<extra></extra>' } as Data);
        }
        return traces;
    }, [r, surface, s.view, s.frame, s.paths, s.fadeTrails, s.starts, s.minima]);
    const max = r ? frames(r) : 0;
    const layout = useMemo<Partial<Layout>>(() => ({ ...baseLayout, margin: { l: 30, r: 20, t: 35, b: 35 }, uirevision: `${r?.experiment_id}-${s.view}-${camera}`, scene: { xaxis: { ...axis, title: { text: 'x' } }, yaxis: { ...axis, title: { text: 'y' } }, zaxis: { ...axis, title: { text: 'f(x, y)' } }, bgcolor: 'transparent', camera: { eye: { x: 1.45, y: 1.45, z: 1.05 } }, aspectmode: 'cube' }, xaxis: { ...axis, title: { text: 'x' }, range: r?.problem.bounds.x }, yaxis: { ...axis, title: { text: 'y' }, range: r?.problem.bounds.y } }), [r, s.view, camera]);
    const download = async () => { if (graph.current) {
        const { default: P } = await import('plotly.js-dist-min');
        await P.downloadImage(graph.current, { format: 'png', filename: 'optimisation-arena', width: 1400, height: 900 });
    } };
    return <section className="panel landscape" ref={container}><div className="tabs" role="tablist" aria-label="Landscape view">{views.map(v => <button key={v.id} role="tab" aria-selected={s.view === v.id} onClick={() => patch({ view: v.id })}>{v.label}</button>)}<button className="icon" aria-label="Expand chart" onClick={() => { if (document.fullscreenElement)
        void document.exitFullscreen();
    else
        void container.current?.requestFullscreen(); }}><Maximize size={16}/></button></div><div className="chart-title"><h2>Search Landscape & Algorithm Paths</h2><span>{r ? r.problem.name : 'Run an experiment to explore the landscape'}</span><small>Replay of the algorithms’ recorded search • drag to rotate / pan</small></div>{r ? <div className="surface-chart" aria-label={`${r.problem.name} objective landscape`}><Plot data={data} layout={layout} useResizeHandler style={{ width: '100%', height: '100%' }} config={{ responsive: true, displaylogo: false, scrollZoom: true, displayModeBar: false }} onError={(error: Error) => setChartError({key: `${r.experiment_id}-${s.view}`, message: error.message})} onInitialized={(_, g) => { graph.current = g as PlotlyHTMLElement; }} onUpdate={(_, g) => { graph.current = g as PlotlyHTMLElement; }}/>{chartError?.key === `${r.experiment_id}-${s.view}` && <p role="alert">Chart unavailable: {chartError.message}. Try the Contour Plot view.</p>}{!surface.length && s.view !== 'paths' && <p role="status">Surface grid unavailable.</p>}</div> : <div className="empty landscape-empty"><div className="empty-orbit">∇</div><h3>A landscape of possibilities</h3><p>Choose your function and algorithms, then run an experiment.<br />Your measured search paths will appear here.</p></div>}
 <div className="playback"><button className="play" aria-label={s.playing ? 'Pause recorded-search replay' : 'Play recorded-search replay'} disabled={!max} onClick={() => { if (!s.playing && window.matchMedia('(prefers-reduced-motion: reduce)').matches)
        patch({ speed: .5 }); patch({ playing: !s.playing, frame: s.frame >= max ? 0 : s.frame }); }}>{s.playing ? <Pause size={18}/> : <Play size={18}/>}</button><input aria-label="Recorded trajectory frame" type="range" min="0" max={max} value={s.frame} disabled={!max} onChange={e => patch({ frame: +e.target.value, playing: false })}/><span>Frame {s.frame} / {max}</span><select aria-label="Playback speed" value={s.speed} onChange={e => patch({ speed: +e.target.value })}>{[.5, 1, 2, 4].map(n => <option key={n} value={n}>{n}×</option>)}</select><button className="icon" aria-label="Reset recorded-search replay" onClick={() => patch({ frame: 0, playing: false })}><RotateCcw size={15}/></button></div>
 {r && <><div className="replay-key" aria-label="Replay marker guide"><span>● Current candidate</span><span>{s.fadeTrails ? `━ Fading recent path (${TRAIL_STEPS} recorded steps)` : '━ Full recorded path to current frame'}</span><span>◆ Best discovery so far</span></div><div className="live-scores">{r.results.map(row => {
    const current = replayAt(r, row.algorithm, s.frame);
    return <span key={row.algorithm}><i style={{background: color(row.algorithm)}}/>{row.display_name}: {current ? `iteration ${current.iteration} · current ${fmt(current.score)} · best ${fmt(current.bestScore)}${current.finished ? ' · final recorded state' : ''}${!current.bestPosition ? ' · best position unavailable' : ''}` : 'No recorded path'}</span>;
 })}</div><p className="replay-note">Replay speed is for explanation. Computation runtime is reported separately.</p></>}
 <div className="chart-actions"><button onClick={() => setCamera(c => c + 1)} disabled={!r}><RotateCcw size={14}/> Reset view</button><button onClick={() => void download()} disabled={!r}><Download size={14}/> Download plot</button></div></section>;
}
export function Convergence() {
    const {state: s} = useExperiment();
    const [axisName, setAxis] = useState<'iterations' | 'function_evaluations'>('iterations');
    const [log, setLog] = useState(false);
    const series = useMemo(() => s.report ? convergence(s.report, axisName) : [], [s.report, axisName]);
    const positive = series.some(a => a.y.length > 0) && series.every(a => a.y.every(v => v > 0));
    const cursors = useMemo(() => s.report ? convergenceAt(s.report, s.frame, axisName) : [], [s.report, s.frame, axisName]);
    const data: Data[] = [
        ...series.map(a => ({type: 'scatter', mode: 'lines', name: a.name, legendgroup: a.id,
            x: a.x, y: a.y, line: {color: color(a.id), width: 2},
            hovertemplate: '%{x} · best %{y:.6g}<extra>%{fullData.name}</extra>',
        } as Data)),
        ...cursors.map(a => ({type: 'scatter', mode: 'markers', name: `${a.name} replay cursor`,
            legendgroup: a.id, showlegend: false, x: [a.x], y: [a.y],
            marker: {color: color(a.id), size: 10, symbol: 'diamond', line: {color: '#ffffff', width: 1}},
            hovertemplate: 'Replay position %{x} · best %{y:.6g}<extra>%{fullData.name}</extra>',
        } as Data)),
    ];
    return <section className="panel convergence"><h2>Convergence Comparison</h2>
        <div className="inline-controls"><select aria-label="Convergence horizontal axis" value={axisName} onChange={e => setAxis(e.target.value as typeof axisName)}><option value="iterations">Iterations / generations</option><option value="function_evaluations">Function evaluations</option></select><label><input type="checkbox" checked={log && positive} disabled={!positive} onChange={e => setLog(e.target.checked)}/> Log scale</label></div>
        {s.report ? <div className="convergence-chart"><Plot data={data} layout={{...baseLayout,
            uirevision: `${s.report.experiment_id}-${axisName}-${log && positive}`,
            xaxis: {...axis, title: {text: axisName === 'iterations' ? 'Iterations / generations' : 'Function evaluations'}},
            yaxis: {...axis, title: {text: 'Best objective value'}, type: log && positive ? 'log' : 'linear'},
            shapes: cursors.map(a => ({type: 'line', xref: 'x', yref: 'paper', x0: a.x, x1: a.x,
                y0: 0, y1: 1, line: {color: color(a.id), width: 1, dash: 'dot'}, opacity: .6, layer: 'below'})),
            legend: {...baseLayout.legend, y: 1.2}, margin: {l: 60, r: 12, t: 52, b: 48},
        }} useResizeHandler style={{width: '100%', height: '100%'}} config={{responsive: true, displaylogo: false, displayModeBar: false}}/></div> : <div className="empty">Convergence histories appear after a run.</div>}
        <p className="footnote">Diamonds and dotted cursors follow each algorithm’s recorded replay state. The full curves show the completed experiment.</p>
        <p className="footnote">{s.report?.convergence.note || 'Compare measured best-so-far objective values.'}{s.report && !positive ? ' Log scale requires all values to be positive.' : ''}</p>
    </section>;
}
