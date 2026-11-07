'use client';

export default function ErrorPage({reset}: {reset: () => void}) {
  return <main className="article" role="alert">
    <span className="eyebrow">WORKSPACE ERROR</span>
    <h1>The workspace could not render.</h1>
    <p>Retry the view. For 3D charts, use a browser with WebGL enabled. Check that the frontend dependencies are installed and the backend is running.</p>
    <button className="primary" onClick={reset}>Retry workspace</button>
  </main>;
}
