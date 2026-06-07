function App() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">AI Procurement Agent</p>
        <h1>Frontend and backend are separated cleanly.</h1>
        <p className="lede">
          React lives in <strong>frontend/</strong> and FastAPI lives in <strong>backend/</strong>.
          Each can be developed and deployed independently.
        </p>
      </section>

      <section className="cards">
        <article className="card">
          <h2>Frontend</h2>
          <p>Vite, React, and TypeScript for the UI.</p>
        </article>
        <article className="card">
          <h2>Backend</h2>
          <p>FastAPI with a health endpoint and Uvicorn entrypoint.</p>
        </article>
      </section>
    </main>
  );
}

export default App;