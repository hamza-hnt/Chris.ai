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
  KeyRound,
  LogOut,
  MessageSquare,
  RefreshCcw,
  ShieldCheck,
  UserRound,
  Users,
  Wrench,
} from "lucide-react";
import "./styles.css";

type Role = "landlord" | "tenant";

type Dashboard = {
  viewer: Person;
  landlord: Person | null;
  role: Role;
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

type LoginResponse = {
  access_token: string;
  user: Person;
};

type DemoUser = Person & {
  identifier: string;
};

type Person = {
  id: string;
  name: string;
  role?: Role;
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

const SESSION_KEY = "chris-demo-session";

function App() {
  const [session, setSession] = useState<LoginResponse | null>(() => {
    const raw = window.localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as LoginResponse) : null;
  });
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(session));
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard(activeSession = session) {
    if (!activeSession) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/portal/dashboard", {
        headers: { "X-User-Id": activeSession.access_token },
      });
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

  function applySession(nextSession: LoginResponse) {
    window.localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    setDashboard(null);
    setSelectedPropertyId(null);
    setSelectedRequestId(null);
    loadDashboard(nextSession);
  }

  function logout() {
    window.localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setDashboard(null);
    setSelectedPropertyId(null);
    setSelectedRequestId(null);
    setError(null);
  }

  useEffect(() => {
    if (session) {
      loadDashboard(session);
    }
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

  if (!session) {
    return <LoginScreen onLogin={applySession} />;
  }

  if (isLoading && !dashboard) {
    return (
      <main className="app-frame app-frame--centered">
        <div className="loading-panel">
          <RefreshCcw className="spin" size={22} />
          <span>Loading operations</span>
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
          <div className="button-row">
            <button className="primary-button" onClick={() => loadDashboard()}>
              <RefreshCcw size={16} />
              Retry
            </button>
            <button className="primary-button" onClick={logout}>
              <LogOut size={16} />
              Sign out
            </button>
          </div>
        </section>
      </main>
    );
  }

  if (!dashboard) return null;

  const isLandlord = dashboard.role === "landlord";

  return (
    <main className="app-frame">
      <header className="topbar">
        <div>
          <p className="eyebrow">{isLandlord ? "Owner operations" : "Tenant portal"}</p>
          <h1>{dashboard.viewer.name}</h1>
          <p className="subtle">
            {isLandlord
              ? "Track every tenant request across your rental portfolio"
              : "Track the progress of your current property requests"}
          </p>
        </div>
        <div className="topbar-actions">
          <span className="viewer-pill">
            <UserRound size={16} />
            {dashboard.viewer.email ?? dashboard.viewer.phone}
          </span>
          <button className="icon-button" onClick={() => loadDashboard()} aria-label="Refresh dashboard">
            <RefreshCcw size={18} />
          </button>
          <button className="icon-button" onClick={logout} aria-label="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className="metrics-grid" aria-label="Portfolio metrics">
        <Metric icon={<Building2 />} label={isLandlord ? "Properties" : "My units"} value={dashboard.metrics.properties} />
        <Metric icon={<Users />} label={isLandlord ? "Tenants" : "Tenant"} value={dashboard.metrics.tenants} />
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
          label={isLandlord ? "Monthly rent" : "Monthly total"}
          value={formatCurrency(dashboard.metrics.monthly_revenue)}
        />
      </section>

      <section className="workspace">
        <aside className="portfolio-panel" aria-label="Properties">
          <div className="section-header">
            <div>
              <p className="eyebrow">{isLandlord ? "Portfolio" : "Rental"}</p>
              <h2>{isLandlord ? "Tenant units" : "My unit"}</h2>
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
                  <small>{isLandlord ? item.tenant.name : `${item.property.type} · ${item.property.size}`}</small>
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
              <h2>{isLandlord ? "Progress by tenant" : "My request progress"}</h2>
            </div>
            <span className="muted-count">{dashboard.requests.length} total</span>
          </div>

          <div className="request-table">
            <div className="request-table-head">
              <span>Request</span>
              <span>{isLandlord ? "Tenant" : "Property"}</span>
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
                <span>{isLandlord ? request.tenant_name : "My rental"}</span>
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
            <RequestDetail request={selectedRequest} property={selectedProperty} role={dashboard.role} />
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

function LoginScreen({ onLogin }: { onLogin: (session: LoginResponse) => void }) {
  const [identifier, setIdentifier] = useState("");
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/auth/demo-users")
      .then((response) => response.json())
      .then((data: { users: DemoUser[] }) => {
        setDemoUsers(data.users);
        setIdentifier(data.users[0]?.identifier ?? "");
      })
      .catch(() => setError("Demo accounts are unavailable."));
  }, []);

  async function submitLogin(nextIdentifier = identifier) {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: nextIdentifier }),
      });
      if (!response.ok) {
        throw new Error("Unknown account.");
      }
      onLogin((await response.json()) as LoginResponse);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Login failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="login-frame">
      <section className="login-panel">
        <div className="login-copy">
          <p className="eyebrow">Chris.AI Portal</p>
          <h1>Property operations, scoped to the signed-in user.</h1>
          <p>
            Owners see every tenant request across their portfolio. Tenants see only their
            own rental and the progress of their requests.
          </p>
        </div>

        <form
          className="login-form"
          onSubmit={(event) => {
            event.preventDefault();
            submitLogin();
          }}
        >
          <span className="login-icon">
            <KeyRound size={20} />
          </span>
          <label htmlFor="identifier">Email or phone</label>
          <input
            id="identifier"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder="marc.landlord@example.com"
          />
          {error ? <p className="form-error">{error}</p> : null}
          <button className="login-button" disabled={isLoading || !identifier.trim()}>
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="demo-users">
          <h2>Demo accounts</h2>
          {demoUsers.map((user) => (
            <button key={user.id} onClick={() => submitLogin(user.identifier)}>
              <span>
                <strong>{user.name}</strong>
                <small>
                  {user.role} · {user.identifier}
                </small>
              </span>
              <ArrowRight size={16} />
            </button>
          ))}
        </div>
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
  role,
}: {
  request: RequestItem;
  property: PropertyPanel | null;
  role: Role;
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
            <h3>{role === "landlord" ? "Tenant and lease" : "My lease"}</h3>
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
