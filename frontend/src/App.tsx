import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Supervisor dashboard</p>
        <h1>Chris.AI</h1>
        <p>
          Bootstrap dashboard placeholder for property-scoped agent supervision,
          interventions, alerts, and operational visibility.
        </p>
        <div className="grid">
          <div>
            <span>Agent status</span>
            <strong>Ready</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>http://localhost:8000</strong>
          </div>
          <div>
            <span>Database</span>
            <strong>PostgreSQL 16</strong>
          </div>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
