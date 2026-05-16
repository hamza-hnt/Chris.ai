import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleDot,
  Clock3,
  Home,
  MessageSquare,
  RefreshCcw,
  ShieldCheck,
  Users,
  Wrench,
} from "lucide-react";
import "./styles.css";

type Dashboard = {
  landlord: Person;
  metrics: {
    properties: number;
    tenants: number;
    open_requests: number;
    blocked_requests: number;
    pending_owner_decisions: number;
    monthly_revenue: number;
    average_progress: number;
  };
  properties: PropertyPanel[];
  requests: RequestItem[];
};

type Person = {
  id: string;
  name: string;
  email?: string;
  phone?: string;
};

type PropertyPanel = {
  property: {
    id: string;
    address: string;
    type: string;
    size?: string;
    status: string;
    equipment: Record<string, unknown>;
    access_details: Record<string, unknown>;
  };
  tenant: Person;
  lease: {
    rent: string;
    charges: string;
    monthly_total: string;
    payment_due_day: number;
    lease_type: string;
    start_date: string;
    end_date?: string | null;
  };
  requests: RequestItem[];
  recent_actions: ActionItem[];
  recent_tool_traces: ToolTrace[];
  recent_conversations: ConversationPreview[];
  trace_count: number;
};

type RequestItem = {
  id: string;
  property_id: string;
  property_address: string;
  tenant_name: string;
  name: string;
  status: "active" | "blocked" | "completed" | "cancelled";
  progress: number;
  next_step: string;
  owner_action_required: boolean;
  steps: Array<{ description: string; status: string; evidence?: string }>;
  created_at?: string;
  updated_at?: string;
};

type ActionItem = {
  id: string;
  kind: string;
  payload: Record<string, unknown>;
  created_at: string;
};

type ToolTrace = {
  id: string;
  turn_id: string;
  tool_name: string;
  created_at: string;
};

type ConversationPreview = {
  id: string;
  party: string;
  thread_id: string;
  updated_at: string;
  message_count: number;
  last_message?: { body?: string; role?: string; channel?: string };
};

function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/supervisor/dashboard");
      if (!response.ok) {
        throw new Error(`Dashboard API returned ${response.status}`);
      }
      const data = (await response.json()) as Dashboard;
      setDashboard(data);
      setSelectedPropertyId((current) => current ?? data.properties[0]?.property.id ?? null);
      setSelectedRequestId((current) => current ?? data.requests[0]?.id ?? null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Dashboard unavailable");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const selectedProperty = useMemo(() => {
    if (!dashboard) return null;
    return (
      dashboard.properties.find((item) => item.property.id === selectedPropertyId) ??
      dashboard.properties[0] ??
      null
    );
  }, [dashboard, selectedPropertyId]);

  const selectedRequest = useMemo(() => {
    if (!dashboard) return null;
    return dashboard.requests.find((request) => request.id === selectedRequestId) ?? null;
  }, [dashboard, selectedRequestId]);

  if (isLoading && !dashboard) {
    return (
      <main className="app-frame app-frame--centered">
        <div className="loading-panel">
          <RefreshCcw className="spin" size={22} />
          <span>Loading portfolio operations</span>
        </div>
      </main>
    );
  }

  if (error && !dashboard) {
    return (
      <main className="app-frame app-frame--centered">
        <section className="empty-state">
          <AlertCircle size={28} />
          <h1>Dashboard unavailable</h1>
          <p>{error}</p>
          <button className="primary-button" onClick={loadDashboard}>
            <RefreshCcw size={16} />
            Retry
          </button>
        </section>
      </main>
    );
  }

  if (!dashboard) return null;

  return (
    <main className="app-frame">
      <header className="topbar">
        <div>
          <p className="eyebrow">Owner operations</p>
          <h1>{dashboard.landlord.name}</h1>
          <p className="subtle">{dashboard.landlord.email ?? dashboard.landlord.phone}</p>
        </div>
        <button className="icon-button" onClick={loadDashboard} aria-label="Refresh dashboard">
          <RefreshCcw size={18} />
        </button>
      </header>

      <section className="metrics-grid" aria-label="Portfolio metrics">
        <Metric icon={<Building2 />} label="Properties" value={dashboard.metrics.properties} />
        <Metric icon={<Users />} label="Tenants" value={dashboard.metrics.tenants} />
        <Metric icon={<Wrench />} label="Open requests" value={dashboard.metrics.open_requests} />
        <Metric
          icon={<AlertCircle />}
          label="Owner decisions"
          value={dashboard.metrics.pending_owner_decisions}
          tone={dashboard.metrics.pending_owner_decisions > 0 ? "warning" : "normal"}
        />
        <Metric
          icon={<ShieldCheck />}
          label="Avg. progress"
          value={`${dashboard.metrics.average_progress}%`}
        />
        <Metric
          icon={<Home />}
          label="Monthly rent"
          value={formatCurrency(dashboard.metrics.monthly_revenue)}
        />
      </section>

      <section className="workspace">
        <aside className="portfolio-panel" aria-label="Properties">
          <div className="section-header">
            <div>
              <p className="eyebrow">Portfolio</p>
              <h2>Tenant units</h2>
            </div>
          </div>
          <div className="property-list">
            {dashboard.properties.map((item) => (
              <button
                key={item.property.id}
                className={`property-row ${
                  item.property.id === selectedProperty?.property.id ? "is-selected" : ""
                }`}
                onClick={() => {
                  setSelectedPropertyId(item.property.id);
                  setSelectedRequestId(item.requests[0]?.id ?? dashboard.requests[0]?.id ?? null);
                }}
              >
                <span className="property-main">
                  <strong>{item.property.address}</strong>
                  <small>{item.tenant.name}</small>
                </span>
                <span className="status-pill">{item.requests.length} requests</span>
              </button>
            ))}
          </div>
        </aside>

        <section className="requests-panel" aria-label="Tenant requests">
          <div className="section-header">
            <div>
              <p className="eyebrow">Requests</p>
              <h2>Progress by tenant</h2>
            </div>
            <span className="muted-count">{dashboard.requests.length} total</span>
          </div>

          <div className="request-table">
            <div className="request-table-head">
              <span>Request</span>
              <span>Tenant</span>
              <span>Status</span>
              <span>Progress</span>
            </div>
            {dashboard.requests.map((request) => (
              <button
                key={request.id}
                className={`request-row ${request.id === selectedRequest?.id ? "is-selected" : ""}`}
                onClick={() => {
                  setSelectedRequestId(request.id);
                  setSelectedPropertyId(request.property_id);
                }}
              >
                <span>
                  <strong>{cleanRequestName(request.name)}</strong>
                  <small>{request.property_address}</small>
                </span>
                <span>{request.tenant_name}</span>
                <span>
                  <StatusPill request={request} />
                </span>
                <span className="progress-cell">
                  <ProgressBar value={request.progress} />
                  <small>{request.progress}%</small>
                </span>
              </button>
            ))}
          </div>
        </section>

        <aside className="detail-panel" aria-label="Request detail">
          {selectedRequest ? (
            <RequestDetail request={selectedRequest} property={selectedProperty} />
          ) : (
            <div className="empty-detail">
              <CircleDot size={22} />
              <p>No request selected</p>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}

function Metric({
  icon,
  label,
  value,
  tone = "normal",
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  tone?: "normal" | "warning";
}) {
  return (
    <div className={`metric metric--${tone}`}>
      <span className="metric-icon">{icon}</span>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RequestDetail({
  request,
  property,
}: {
  request: RequestItem;
  property: PropertyPanel | null;
}) {
  return (
    <div className="detail-stack">
      <div className="detail-heading">
        <div>
          <p className="eyebrow">Request detail</p>
          <h2>{cleanRequestName(request.name)}</h2>
        </div>
        <StatusPill request={request} />
      </div>

      <div className="decision-strip">
        {request.owner_action_required ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
        <span>
          {request.owner_action_required
            ? "Owner decision is pending"
            : "Chris can continue without owner input"}
        </span>
      </div>

      <div className="progress-block">
        <div className="progress-label">
          <span>Request progress</span>
          <strong>{request.progress}%</strong>
        </div>
        <ProgressBar value={request.progress} />
      </div>

      <section className="detail-section">
        <h3>Next action</h3>
        <p>{request.next_step}</p>
      </section>

      <section className="detail-section">
        <h3>Plan steps</h3>
        <ol className="step-list">
          {request.steps.map((step, index) => (
            <li key={`${request.id}-${index}`} className={`step step--${step.status}`}>
              <span className="step-marker">
                {step.status === "done" ? <CheckCircle2 size={16} /> : <Clock3 size={16} />}
              </span>
              <span>
                <strong>{step.description}</strong>
                {step.evidence ? <small>{step.evidence}</small> : null}
              </span>
            </li>
          ))}
        </ol>
      </section>

      {property ? (
        <>
          <section className="detail-section">
            <h3>Tenant and lease</h3>
            <div className="facts-grid">
              <Fact label="Tenant" value={property.tenant.name} />
              <Fact label="Phone" value={property.tenant.phone ?? "Not set"} />
              <Fact label="Monthly total" value={formatCurrency(Number(property.lease.monthly_total))} />
              <Fact label="Due day" value={`Day ${property.lease.payment_due_day}`} />
            </div>
          </section>

          <section className="detail-section">
            <h3>Recent activity</h3>
            <div className="activity-list">
              {property.recent_actions.slice(0, 4).map((action) => (
                <div className="activity-row" key={action.id}>
                  <MessageSquare size={15} />
                  <span>
                    <strong>{action.kind}</strong>
                    <small>{formatDateTime(action.created_at)}</small>
                  </span>
                </div>
              ))}
              {property.recent_tool_traces.slice(0, 4).map((trace) => (
                <div className="activity-row" key={trace.id}>
                  <ArrowRight size={15} />
                  <span>
                    <strong>{trace.tool_name}</strong>
                    <small>{formatDateTime(trace.created_at)}</small>
                  </span>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function StatusPill({ request }: { request: RequestItem }) {
  const label = request.owner_action_required ? "Decision" : request.status;
  return <span className={`status-pill status-pill--${request.status}`}>{label}</span>;
}

function ProgressBar({ value }: { value: number }) {
  return (
    <span className="progress-track" aria-label={`Progress ${value}%`}>
      <span className="progress-fill" style={{ width: `${Math.min(value, 100)}%` }} />
    </span>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <span className="fact">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}

function cleanRequestName(name: string) {
  return name.replace(/^Request:\s*/i, "");
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
