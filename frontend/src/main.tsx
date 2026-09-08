import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowRight,
  Box,
  Check,
  ChevronRight,
  Database,
  Disc3,
  HardDrive,
  Layers,
  LoaderCircle,
  Network,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import "./style.css";

type Page =
  | "Dashboard"
  | "Image Library"
  | "Golden Image Deployment"
  | "Driver Packs"
  | "Build Capsule"
  | "Jobs"
  | "PXE Integration"
  | "Storage";
type Analysis = {
  detected?: Record<string, string>;
  paths?: Record<string, boolean>;
  recommended_adapter?: string;
  evidence?: string[];
  iso9660?: boolean;
  eltorito?: boolean;
  volume_id?: string;
};
type Media = {
  id: number;
  name: string;
  size_bytes: number;
  storage_id: number;
  relative_path: string;
  sha256?: string;
  analysis?: Analysis;
};
type Job = {
  id: number;
  kind: string;
  status: string;
  progress: number;
  log: string;
  result?: Analysis & { media_id?: number };
};
type Storage = {
  id: number;
  name: string;
  path: string;
  kind: string;
  role: string;
  enabled: boolean;
};
type StorageStatus = {
  online: boolean;
  free_bytes?: number;
  total_bytes?: number;
};
const groups: { label: string; items: [Page, LucideIcon][] }[] = [
  { label: "Overview", items: [["Dashboard", Activity]] },
  {
    label: "Media",
    items: [
      ["Image Library", Disc3],
      ["Driver Packs", HardDrive],
    ],
  },
  {
    label: "Build & deploy",
    items: [
      ["Build Capsule", Box],
      ["Golden Image Deployment", Layers],
      ["Jobs", Activity],
      ["PXE Integration", Network],
    ],
  },
  { label: "Administration", items: [["Storage", Database]] },
];
const subtitles: Record<Page, string> = {
  Dashboard: "Control plane overview and deployment readiness",
  "Image Library": "Register, inspect and organize deployment images",
  "Golden Image Deployment": "Reference images for repeatable bare-metal deployment",
  "Driver Packs": "Hardware-aware drivers for deployment specialization",
  "Build Capsule": "Prepare media for Heimdal Network OS Deployment",
  Jobs: "Follow media processing and inspect job logs",
  "PXE Integration": "Connect deployment artifacts to your boot infrastructure",
  Storage: "Manage the external locations that hold your media",
};
const bytes = (n?: number) =>
  n === undefined
    ? "Unavailable"
    : n === 0
      ? "0 B"
      : `${(n / 1024 ** Math.min(4, Math.floor(Math.log(n) / Math.log(1024)))).toFixed(1)} ${["B", "KiB", "MiB", "GiB", "TiB"][Math.min(4, Math.floor(Math.log(n) / Math.log(1024)))]}`;
const adapter = (s?: string) =>
  ({
    "linux-kernel-initrd": "Linux kernel / initrd",
    "uefi-chainload": "UEFI chainload",
    grub: "GRUB",
    isolinux: "ISOLINUX",
    unknown: "Needs review",
  })[s || "unknown"] || s;
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api/v1${path}`, init);
  const text = await r.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(
      r.status === 413
        ? "The server rejected this upload because it exceeds its size limit. Register the file on mounted storage instead."
        : `The server returned an unexpected response (${r.status}).`,
    );
  }
  if (!r.ok) {
    const detail = (data as { detail?: unknown })?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${r.status}). Check your input and try again.`,
    );
  }
  return data as T;
}
const post = <T,>(path: string, data: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Empty({
  icon: Icon = Disc3,
  title,
  children,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={27} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
function Heading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}
// Recorded lab evidence; this is not live appliance or per-media readiness.
function LabValidation() {
  return (
    <section className="panel lab-validation" aria-label="Recorded lab validation">
      <Heading title="Lab validation" description="Automatic boot chain passed · 6 September 2026 · isolated QEMU lab" />
      <div className="grid three">
        <div>
          <Badge tone="green">Passed in lab</Badge>
          <h3>PXE → WinPE → launcher</h3>
          <p>Unattended network boot completed in 144.6 seconds. The launcher ran its stage and returned the expected code, 37.</p>
          <p>Missing-image control passed in 17.0 seconds.</p>
        </div>
        <div>
          <Badge tone="green">Passed in lab</Badge>
          <h3>Capsule → UEFI → Ubuntu</h3>
          <p>The generated lab capsule completed a one-time UEFI reboot in 175.6 seconds, preserving the normal boot order.</p>
          <p>Ubuntu reached its installer automatically in 17 minutes 26 seconds. Missing and invalid EFI controls passed.</p>
        </div>
        <div>
          <Badge>Unverified</Badge>
          <h3>Heimdal integration</h3>
          <p>Validation through the actual Heimdal deployment process is still pending.</p>
          <p>Next: build a Windows golden-image capsule from a customer WIM, validate it in the harness, then through Heimdal.</p>
        </div>
      </div>
      <p className="help">These recorded lab results do not validate individual library images, physical hardware, or Secure Boot. They are not a live readiness check.</p>
      <details>
        <summary>View recorded test evidence</summary>
        <dl>
          <dt>Network boot · passed · 6 September 2026, 00:33:52 UTC</dt>
          <dd>Run: <code>winpe-pxe-20260906T003352.579436Z</code>. DHCP, both TFTP bootstrap requests, all eight HTTP transfers, and all three guest execution markers verified.</dd>
          <dt>Missing-image control · passed · 6 September 2026, 00:36:46 UTC</dt>
          <dd>Run: <code>winpe-pxe-20260906T003646.958113Z</code>. Missing WIM returned HTTP 404; no WinPE execution markers appeared.</dd>
          <dt>Generated capsule handoff · passed · 6 September 2026, 01:03:59 UTC</dt>
          <dd>Run: <code>winpe-pxe-20260906T010359.765597Z</code>. One guest reboot, unchanged BootOrder, consumed BootNext, and temporary firmware-variable cleanup verified.</dd>
          <dt>Ubuntu installer handoff · passed · 6 September 2026, 01:52:49 UTC</dt>
          <dd>Run: <code>winpe-pxe-20260906T015249.555025Z</code> (1046.2 seconds). Full PXE and capsule boot chain reached Subiquity with no keyboard input; BootCurrent matched and firmware-variable deletion was read back.</dd>
          <dt>EFI rejection controls · passed</dt>
          <dd>Missing stage: <code>winpe-pxe-20260906T010801.293915Z</code> (168.9 seconds). Invalid stage: <code>winpe-pxe-20260906T011119.375712Z</code> (185.8 seconds). Both rejected the payload without rebooting.</dd>
        </dl>
        <p>Reports and logs are retained with these run IDs in the lab artifacts. Reproduction and scope are documented in <code>docs/PXE_TEST_LAB.md</code> and <code>docs/HANDOFF_TEST_LAB.md</code>.</p>
      </details>
    </section>
  );
}
function JobTable({
  jobs,
  onSelect,
}: {
  jobs: Job[];
  onSelect: (id: number) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Job</th>
            <th>Type</th>
            <th>Status</th>
            <th>Progress</th>
            <th>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>
                <b>#{j.id}</b>
                <small>{j.result?.volume_id || "Media processing"}</small>
              </td>
              <td>{j.kind.replaceAll("-", " ")}</td>
              <td>
                <Badge
                  tone={
                    j.status === "complete"
                      ? "green"
                      : j.status === "failed"
                        ? "red"
                        : "blue"
                  }
                >
                  {j.status}
                </Badge>
              </td>
              <td>
                <div
                  className="progress"
                  role="progressbar"
                  aria-label={`Job ${j.id}`}
                  aria-valuenow={j.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <span style={{ width: `${j.progress}%` }} />
                </div>
                <small>{j.progress}%</small>
              </td>
              <td>
                <button className="text-button" onClick={() => onSelect(j.id)}>
                  View log <ChevronRight size={14} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function App() {
  const [page, setPage] = useState<Page>("Dashboard"),
    [media, setMedia] = useState<Media[]>([]),
    [jobs, setJobs] = useState<Job[]>([]),
    [stores, setStores] = useState<Storage[]>([]),
    [statuses, setStatuses] = useState<Record<number, StorageStatus>>({});
  const [connection, setConnection] = useState<
      "loading" | "online" | "offline"
    >("loading"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [refreshing, setRefreshing] = useState(false),
    [loaded, setLoaded] = useState(false),
    [readOnly, setReadOnly] = useState(false);
  const [modal, setModal] = useState(false),
    [selectedMedia, setSelectedMedia] = useState(""),
    [selectedJob, setSelectedJob] = useState<number>(),
    [search, setSearch] = useState("");
  const fetching = useRef(false);
  const refresh = useCallback(async () => {
    if (fetching.current) return;
    fetching.current = true;
    setRefreshing(true);
    try {
      const [health, m, j, s] = await Promise.all([
        api<{storage_read_only?: boolean}>("/health"),
        api<Media[]>("/media"),
        api<Job[]>("/jobs"),
        api<Storage[]>("/storage"),
      ]);
      setReadOnly(Boolean(health.storage_read_only));
      setMedia(m);
      setJobs(j);
      setStores(s);
      setConnection("online");
      setLoaded(true);
      setError("");
      const results = await Promise.all(
        s.map(async (x) => {
          try {
            return [
              x.id,
              await api<StorageStatus>(`/storage/${x.id}/status`),
            ] as const;
          } catch {
            return [x.id, { online: false }] as const;
          }
        }),
      );
      setStatuses(Object.fromEntries(results));
    } catch (e) {
      setConnection("offline");
      setError(
        e instanceof Error ? e.message : "Unable to reach the appliance.",
      );
    } finally {
      fetching.current = false;
      setRefreshing(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  const go = (p: Page) => {
    setPage(p);
    window.scrollTo({ top: 0 });
  };
  const openJob = (id: number) => {
    setSelectedJob(id);
    go("Jobs");
  };
  const current = media.find((m) => String(m.id) === selectedMedia) || media[0];
  const job = jobs.find((j) => j.id === selectedJob) || jobs[0];
  const active = jobs.filter((j) =>
    ["queued", "running"].includes(j.status),
  ).length;
  const number = (n: number) => (loaded ? n : "—");
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            go("Dashboard");
          }}
        >
          <span className="brand-mark">
            <ShieldCheck size={25} />
          </span>
          <span>
            <strong>Bare-Metal Adapter</strong>
            <small>HEIMDAL DEPLOYMENT PLATFORM</small>
          </span>
        </a>
        <nav aria-label="Main navigation">
          {groups.map((g) => (
            <div className="nav-group" key={g.label}>
              <div className="nav-label">{g.label}</div>
              {g.items.map(([p, Icon]) => (
                <button
                  key={p}
                  title={p}
                  className={`nav-item ${page === p ? "active" : ""}`}
                  aria-current={page === p ? "page" : undefined}
                  onClick={() => go(p)}
                >
                  <Icon size={18} />
                  <span>{p}</span>
                  {p === "Jobs" && active > 0 && <em>{active}</em>}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Server size={17} />
          <div>
            <strong>Management appliance</strong>
            <small>Platform foundation · v0.1</small>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <div className="breadcrumb">
              Workspace <ChevronRight size={12} /> {page}
            </div>
            <h1>{page}</h1>
          </div>
          <div className="top-actions">
            <Badge
              tone={
                connection === "online"
                  ? "green"
                  : connection === "offline"
                    ? "orange"
                    : "neutral"
              }
            >
              <span className="status-dot" />
              {connection === "online"
                ? "API connected"
                : connection === "offline"
                  ? "API unavailable"
                  : "Connecting"}
            </Badge>
            <button
              className="icon-button"
              aria-label="Refresh data"
              disabled={refreshing}
              onClick={() => void refresh()}
            >
              <RefreshCw size={17} className={refreshing ? "spin" : ""} />
            </button>
            <button className="primary" onClick={() => setModal(true)}>
              <Plus size={16} /> Add image
            </button>
          </div>
        </header>
        <div className="content">
          <p className="page-subtitle">{subtitles[page]}</p>
          {error && (
            <div className="banner error" role="alert">
              <div>
                <strong>Could not refresh appliance data.</strong>
                <p>
                  {error}{" "}
                  {loaded
                    ? "Previously loaded records are shown."
                    : "Start the API to load your library."}
                </p>
              </div>
              <button onClick={() => void refresh()}>Retry</button>
            </div>
          )}
          {page === "Dashboard" && (
            <>
              <section className="hero">
                <div>
                  <div className="eyebrow">YOUR DEPLOYMENT CONTROL CENTER</div>
                  <h2>
                    From deployment images{" "}
                    <br />
                    to bare-metal deployment.
                  </h2>
                  <p>
                    One workspace to inspect images, prepare deployment
                    capsules, and manage the images behind your Heimdal
                    workflows.
                  </p>
                  <div className="button-row">
                    <button className="primary" onClick={() => setModal(true)}>
                      <Plus size={16} /> Add deployment image
                    </button>
                    <button
                      className="hero-button"
                      onClick={() => go("Build Capsule")}
                    >
                      Prepare a capsule <ArrowRight size={16} />
                    </button>
                  </div>
                </div>
                <div className="hero-stats">
                  {[
                    ["Images", number(media.length)],
                    ["Storage locations", number(stores.length)],
                    ["Active jobs", number(active)],
                    [
                      "Completed jobs",
                      number(
                        jobs.filter((j) => j.status === "complete").length,
                      ),
                    ],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <strong>{value}</strong>
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </section>
              <LabValidation />
              <Heading
                title="Your deployment workflow"
                description="Start with a storage location, then inspect your first image."
              />
              <div className="grid three">
                {[
                  {
                    n: "01",
                    icon: Database,
                    title: "Connect your storage",
                    text: "Register a mounted share to keep deployment media outside the appliance.",
                    page: "Storage" as Page,
                  },
                  {
                    n: "02",
                    icon: Disc3,
                    title: "Inspect deployment images",
                    text: "Discover boot structures and review candidate deployment adapters.",
                    page: "Image Library" as Page,
                  },
                  {
                    n: "03",
                    icon: Box,
                    title: "Prepare a capsule",
                    text: "Review source compatibility. Capsule generation is coming next.",
                    page: "Build Capsule" as Page,
                  },
                ].map((x) => (
                  <button
                    className="workflow-card"
                    key={x.n}
                    onClick={() => go(x.page)}
                  >
                    <div className="workflow-top">
                      <span className="tile-icon">
                        <x.icon size={21} />
                      </span>
                      <span>{x.n}</span>
                    </div>
                    <h3>{x.title}</h3>
                    <p>{x.text}</p>
                    <span className="workflow-link">
                      Open workspace <ArrowRight size={15} />
                    </span>
                  </button>
                ))}
              </div>
              <Heading
                title="Recent activity"
                description="Latest analysis and processing jobs"
                action={
                  <button className="text-button" onClick={() => go("Jobs")}>
                    View all jobs <ArrowRight size={15} />
                  </button>
                }
              />
              {jobs.length ? (
                <JobTable jobs={jobs.slice(0, 5)} onSelect={openJob} />
              ) : (
                <section className="panel">
                  <Empty
                    icon={Activity}
                    title={loaded ? "No jobs yet" : "Waiting for job data"}
                  >
                    Analysis jobs will appear here as you add media.
                  </Empty>
                </section>
              )}
              <div className="storage-note">
                <Database size={20} />
                <div>
                  <strong>
                    Control plane in the VM. Media on your storage.
                  </strong>
                  <p>
                    Deployment images and future build outputs
                    belong in your external library.
                  </p>
                </div>
                <button className="text-button" onClick={() => go("Storage")}>
                  Manage storage <ArrowRight size={15} />
                </button>
              </div>
            </>
          )}
          {page === "Image Library" && (
            <>
              <Heading
                title="Image Library"
                description="Inspect deployment images on a share or upload a file. ISO inspection is available; WIM support is planned."
                action={
                  <button className="primary" onClick={() => setModal(true)}>
                    <Plus size={16} /> Add image
                  </button>
                }
              />
              <button className="dropzone" onClick={() => setModal(true)}>
                <span className="tile-icon">
                  <Upload size={26} />
                </span>
                <h3>Add your deployment image</h3>
                <p>
                  Select an ISO file or register an existing file on mounted
                  storage.
                </p>
                <span className="button-like">
                  Choose a source <ArrowRight size={15} />
                </span>
              </button>
              <div className="section-heading">
                <h2>
                  Registered images{" "}
                  <span className="count">{number(media.length)}</span>
                </h2>
                <label className="search">
                  <Search size={16} />
                  <input
                    aria-label="Search images"
                    placeholder="Search your library…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
              </div>
              {media.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Image</th>
                        <th>Size</th>
                        <th>Architecture</th>
                        <th>Candidate adapter</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {media
                        .filter((m) =>
                          m.name.toLowerCase().includes(search.toLowerCase()),
                        )
                        .map((m) => (
                          <tr key={m.id}>
                            <td>
                              <div className="media-name">
                                <Disc3 size={20} />
                                <div>
                                  <b>{m.name}</b>
                                  <small>
                                    {stores.find((s) => s.id === m.storage_id)
                                      ?.name || `Storage #${m.storage_id}`}
                                  </small>
                                </div>
                              </div>
                            </td>
                            <td>{bytes(m.size_bytes)}</td>
                            <td>
                              {m.analysis?.detected?.architecture || "Unknown"}
                            </td>
                            <td>{adapter(m.analysis?.recommended_adapter)}</td>
                            <td>
                              <Badge
                                tone={
                                  m.analysis?.recommended_adapter &&
                                  m.analysis.recommended_adapter !== "unknown"
                                    ? "blue"
                                    : "orange"
                                }
                              >
                                {m.analysis?.recommended_adapter &&
                                m.analysis.recommended_adapter !== "unknown"
                                  ? "Analyzed"
                                  : "Needs review"}
                              </Badge>
                            </td>
                            <td>
                              <button
                                className="text-button"
                                onClick={() => {
                                  setSelectedMedia(String(m.id));
                                  go("Build Capsule");
                                }}
                              >
                                Inspect <ChevronRight size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                  {!media.some((m) =>
                    m.name.toLowerCase().includes(search.toLowerCase()),
                  ) && (
                    <p className="no-results">No images match “{search}”.</p>
                  )}
                </div>
              ) : (
                <section className="panel">
                  <Empty
                    title={
                      loaded
                        ? "Your library is ready for its first image"
                        : "Library data unavailable"
                    }
                  >
                    Add a source to queue an analysis job. Completed analyses
                    appear here.
                  </Empty>
                </section>
              )}
            </>
          )}
          {page === "Build Capsule" && (
            <>
              <Heading
                title="Create deployment capsule"
                description="Review your source and its detected boot profile."
              />
              <div className="steps">
                {["Source", "Analyze", "Adapter", "Build", "Validate"].map(
                  (s, i) => (
                    <div
                      key={s}
                      className={
                        i < 2 && current
                          ? "done"
                          : i === 2 && current
                            ? "active"
                            : ""
                      }
                    >
                      <span>
                        {i < 2 && current ? <Check size={13} /> : i + 1}
                      </span>
                      {s}
                    </div>
                  ),
                )}
              </div>
              {current ? (
                <div className="grid analysis-layout">
                  <section className="panel">
                    <label className="field">
                      Source image
                      <select
                        value={String(current.id)}
                        onChange={(e) => setSelectedMedia(e.target.value)}
                      >
                        {media.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <Heading
                      title="Detected image profile"
                      description={current.analysis?.volume_id || current.name}
                    />
                    <div className="profile-grid">
                      {Object.entries({
                        Architecture:
                          current.analysis?.detected?.architecture || "Unknown",
                        "OS family":
                          current.analysis?.detected?.family || "Unknown",
                        ISO9660: current.analysis?.iso9660
                          ? "Detected"
                          : "Not detected",
                        "El Torito": current.analysis?.eltorito
                          ? "Present"
                          : "Not detected",
                        "Installer layout":
                          current.analysis?.detected?.linux_layout || "Unknown",
                        Size: bytes(current.size_bytes),
                      }).map(([k, v]) => (
                        <div className="kv" key={k}>
                          <span>{k}</span>
                          <strong>{v}</strong>
                        </div>
                      ))}
                    </div>
                    <Heading title="Detection evidence" />
                    {current.analysis?.evidence?.length ? (
                      <ul className="evidence">
                        {current.analysis.evidence.map((e) => (
                          <li key={e}>
                            <Check size={15} />
                            {e}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No detection evidence recorded.</p>
                    )}
                    <details>
                      <summary>File paths and checksum</summary>
                      <pre className="file-details">
                        {Object.keys(current.analysis?.paths || {}).join(
                          "\n",
                        ) || "No recognized paths"}
                        {"\n\n"}SHA-256: {current.sha256 || "Unavailable"}
                      </pre>
                    </details>
                  </section>
                  <section className="panel adapter-panel">
                    <span className="tile-icon">
                      <Box size={23} />
                    </span>
                    <h3>Candidate adapter</h3>
                    <div className="recommendation">
                      <strong>
                        {adapter(current.analysis?.recommended_adapter)}
                      </strong>
                      <p>
                        Suggested by media inspection. Boot compatibility has
                        not yet been validated.
                      </p>
                    </div>
                    <h4>Deployment readiness</h4>
                    <p className="readiness">
                      <Check size={16} /> Source analysis available
                    </p>
                    <p className="readiness muted">
                      ○ Capsule engine not available
                    </p>
                    <p className="readiness muted">
                      ○ Target boot validation pending
                    </p>
                    <button className="primary full" disabled>
                      <Box size={16} /> Create Heimdal capsule
                    </button>
                    <p className="help">
                      Capsule generation will be enabled when the adapter engine
                      is implemented.
                    </p>
                  </section>
                </div>
              ) : (
                <section className="panel">
                  <Empty
                    icon={Box}
                    title="Start with an analyzed image"
                    action={
                      <button
                        className="primary"
                        onClick={() => setModal(true)}
                      >
                        Add source media <ArrowRight size={15} />
                      </button>
                    }
                  >
                    Add an image and complete analysis to review its deployment profile
                    here.
                  </Empty>
                </section>
              )}
            </>
          )}
          {page === "Jobs" && (
            <>
              <Heading
                title="Processing jobs"
                description="Analysis progress and diagnostic output from the worker."
                action={
                  <Badge tone={active ? "blue" : "neutral"}>
                    {active} active
                  </Badge>
                }
              />
              {jobs.length ? (
                <>
                  <JobTable jobs={jobs} onSelect={setSelectedJob} />
                  <Heading
                    title={`Job #${job.id} log`}
                    description="Output reported by the processing worker"
                  />
                  <pre className="log" aria-label="Selected job log">
                    {job.log || "Waiting for worker output…"}
                  </pre>
                </>
              ) : (
                <section className="panel">
                  <Empty
                    icon={Activity}
                    title={loaded ? "No jobs yet" : "Waiting for job data"}
                  >
                    Add media to start the first analysis job.
                  </Empty>
                </section>
              )}
            </>
          )}
          {page === "Storage" && (
            <StoragePage
              stores={stores}
              statuses={statuses}
              refresh={refresh}
              notify={setNotice}
            />
          )}
          {(page === "Golden Image Deployment" || page === "Driver Packs") && (
            <>
              <Heading
                title={
                  page === "Golden Image Deployment"
                    ? "Windows golden-image deployment"
                    : "Driver repository"
                }
                action={<Badge tone="orange">Planned capability</Badge>}
              />
              <section className="panel">
                <Empty
                  icon={page === "Golden Image Deployment" ? Layers : HardDrive}
                  title={
                    page === "Golden Image Deployment"
                      ? "Deploy your Windows image through Heimdal"
                      : "Prepare for hardware-aware deployment"
                  }
                >
                  {page === "Golden Image Deployment"
                    ? "The first production use case will deploy a customer-prepared, generalized Windows WIM through Heimdal without Configuration Manager (SCCM). WIM import, image application, and capsule generation are planned; they are not available yet."
                    : "Driver imports, hardware matching, and deployment injection are planned. These workflows are not available yet."}
                </Empty>
              </section>
              <div className="grid three">
                {(page === "Golden Image Deployment"
                  ? [
                      "Select a generalized WIM",
                      "Configure deployment and drivers",
                      "Build a capsule and validate through Heimdal",
                    ]
                  : [
                      "Import vendor packs",
                      "Match target hardware",
                      "Apply during deployment",
                    ]
                ).map((t, i) => (
                  <section className="panel planned-card" key={t}>
                    <span className="step-number">0{i + 1}</span>
                    <h3>{t}</h3>
                    <Badge>Coming later</Badge>
                  </section>
                ))}
              </div>
            </>
          )}
          {page === "PXE Integration" && (
            <>
              <Heading
                title="Deployment integrations"
                description="Heimdal is the primary deployment transport."
              />
              <LabValidation />
              <div className="grid two">
                <section className="panel integration">
                  <span className="tile-icon">
                    <Network size={25} />
                  </span>
                  <div className="section-heading">
                    <h3>Heimdal Network OS Deployment</h3>
                    <Badge tone="orange">Experimental</Badge>
                  </div>
                  <p>
                    Prepare deployment media for Heimdal’s WinPE and setup.exe
                    workflow.
                  </p>
                  <div className="banner">
                    <p>
                      The isolated lab passed the full PXE → WinPE → capsule → UEFI →
                      Ubuntu installer boot sequence without keyboard input. Actual
                      Heimdal deployment remains unverified. Capsule generation in
                      the app, connection testing, and publishing are not available yet.
                    </p>
                  </div>
                  <button disabled className="primary">
                    <Upload size={16} /> Publish capsule
                  </button>
                </section>
                <section className="panel integration">
                  <span className="tile-icon">
                    <Server size={25} />
                  </span>
                  <div className="section-heading">
                    <h3>Standalone PXE</h3>
                    <Badge>Reserved</Badge>
                  </div>
                  <p>
                    An optional future boot service for environments that need a
                    separate deployment path.
                  </p>
                  <div className="banner">
                    <p>
                      Disabled by default. No standalone PXE service is
                      implemented in this release.
                    </p>
                  </div>
                  <button disabled>Configure integration</button>
                </section>
              </div>
            </>
          )}
          <footer>
            Heimdal Bare-Metal Adapter{" "}
            <span>External-first deployment management</span>
          </footer>
        </div>
      </main>
      {modal && (
        <ImportModal
          readOnly={readOnly}
          stores={stores}
          onClose={() => setModal(false)}
          onStorage={() => {
            setModal(false);
            go("Storage");
          }}
          onQueued={(id) => {
            setModal(false);
            setNotice(`Analysis job #${id} queued`);
            void refresh();
            openJob(id);
          }}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          <Check size={18} />
          {notice}
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
function StoragePage({
  stores,
  statuses,
  refresh,
  notify,
}: {
  stores: Storage[];
  statuses: Record<number, StorageStatus>;
  refresh: () => Promise<void>;
  notify: (s: string) => void;
}) {
  const [adding, setAdding] = useState(false),
    [name, setName] = useState(""),
    [path, setPath] = useState("/storage/iso"),
    [role, setRole] = useState("media"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post("/storage", {
        name: name.trim(),
        path: path.trim(),
        kind: "mounted",
        role,
      });
      setAdding(false);
      setName("");
      notify("Storage location registered");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Heading
        title="External storage"
        description="Register paths already mounted and accessible to the appliance."
        action={
          <button className="primary" onClick={() => setAdding(!adding)}>
            <Plus size={16} /> Add storage
          </button>
        }
      />
      {adding && (
        <form className="panel storage-form" onSubmit={submit}>
          <h3>Register a mounted location</h3>
          <p className="help">
            Use the path visible to the API and worker. Container installations
            usually expose shares under /storage.
          </p>
          <div className="form-grid">
            <label className="field">
              Display name
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Deployment media"
                maxLength={120}
              />
            </label>
            <label className="field">
              Mounted path
              <input
                required
                value={path}
                onChange={(e) => setPath(e.target.value)}
                pattern="/.*"
                placeholder="/storage/iso"
              />
            </label>
            <label className="field">
              Purpose
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="media">Installer media</option>
                <option value="golden-images">Golden images</option>
                <option value="drivers">Driver packs</option>
                <option value="output">Build output</option>
              </select>
            </label>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="button-row">
            <button className="primary" disabled={busy}>
              {busy ? "Registering…" : "Register storage"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setAdding(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {stores.length ? (
        <div className="grid three">
          {stores.map((s) => (
            <section className="panel storage-card" key={s.id}>
              <div className="storage-card-top">
                <span className="tile-icon teal">
                  <Database size={23} />
                </span>
                <Badge
                  tone={
                    !s.enabled
                      ? "neutral"
                      : statuses[s.id]?.online
                        ? "green"
                        : "orange"
                  }
                >
                  {!s.enabled
                    ? "Disabled"
                    : statuses[s.id]?.online
                      ? "Path available"
                      : statuses[s.id]
                        ? "Unavailable"
                        : "Checking"}
                </Badge>
              </div>
              <h3>{s.name}</h3>
              <code>{s.path}</code>
              <div className="chips">
                <Badge>{s.kind}</Badge>
                <Badge>{s.role}</Badge>
              </div>
              <div className="capacity">
                <span>Available capacity</span>
                <strong>{bytes(statuses[s.id]?.free_bytes)}</strong>
              </div>
              <p className="help">
                Capacity is reported by the backing filesystem. Mount identity
                is not verified.
              </p>
            </section>
          ))}
        </div>
      ) : (
        <section className="panel">
          <Empty
            icon={Database}
            title="Connect your media library"
            action={
              <button onClick={() => setAdding(true)}>
                Register a location <ArrowRight size={15} />
              </button>
            }
          >
            Mount your shared storage, then register the path to start analyzing
            media.
          </Empty>
        </section>
      )}
      <div className="storage-note">
        <ShieldCheck size={23} />
        <div>
          <strong>Keep the appliance small</strong>
          <p>
            Use external storage for ISOs, golden images, drivers, and
            deployment artifacts.
          </p>
        </div>
      </div>
    </>
  );
}
function ImportModal({
  readOnly,
  stores,
  onClose,
  onStorage,
  onQueued,
}: {
  stores: Storage[];
  onClose: () => void;
  onStorage: () => void;
  onQueued: (id: number) => void;
  readOnly: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [mode, setMode] = useState<"existing" | "upload">("existing"),
    [sid, setSid] = useState(String(stores.find((s) => s.enabled)?.id || "")),
    [path, setPath] = useState(""),
    [file, setFile] = useState<File>(),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [drag, setDrag] = useState(false);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  const selectFile = (f?: File) => {
    if (f && !f.name.toLowerCase().endsWith(".iso")) {
      setError("Choose a file with an .iso extension.");
      return;
    }
    setFile(f);
    setError("");
  };
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      let relative = path.trim();
      if (mode === "upload") {
        if (!file) throw new Error("Choose an ISO file.");
        const body = new FormData();
        body.append("file", file);
        const result = await api<{ relative_path: string }>(
          `/media/upload?storage_id=${encodeURIComponent(sid)}`,
          { method: "POST", body },
        );
        relative = result.relative_path;
        setPath(relative);
        setMode("existing");
        setFile(undefined);
      }
      const result = await post<{ job_id: number }>("/media/analyze", {
        storage_id: Number(sid),
        relative_path: relative,
      });
      onQueued(result.job_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="modal"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="import-title"
    >
      <div className="modal-heading">
        <span className="tile-icon">
          <Disc3 size={23} />
        </span>
        <button
          className="icon-button"
          aria-label="Close dialog"
          disabled={busy}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <h2 id="import-title">Add deployment image</h2>
      <p>Choose your source. ISO inspection is currently supported; WIM import and deployment are planned. Analysis runs as a background job.</p>
      {stores.some((s) => s.enabled) ? (
        <form onSubmit={submit}>
          <div className="segmented">
            <button
              type="button"
              disabled={busy}
              aria-pressed={mode === "existing"}
              className={mode === "existing" ? "selected" : ""}
              onClick={() => setMode("existing")}
            >
              <Database size={15} /> On mounted storage
            </button>
            <button
              type="button"
              disabled={busy || readOnly}
              aria-pressed={mode === "upload"}
              className={mode === "upload" ? "selected" : ""}
              onClick={() => setMode("upload")}
            >
              <Upload size={15} /> Upload a file
            </button>
          </div>
          {readOnly && <p className="help">This library is read-only. Analyze an ISO already on the shared drive.</p>}
          <fieldset disabled={busy}>
            <label className="field">
              Storage location
              <select
                required
                value={sid}
                onChange={(e) => setSid(e.target.value)}
              >
                {stores
                  .filter((s) => s.enabled)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} — {s.path}
                    </option>
                  ))}
              </select>
            </label>
            {mode === "existing" ? (
              <label className="field">
                Relative ISO path
                <input
                  required
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="ubuntu-server-amd64.iso"
                />
                <span className="help">
                  Path within the selected storage location. The file stays in
                  place.
                </span>
              </label>
            ) : (
              <>
                <div
                  className={`file-drop ${drag ? "drag" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDrag(false);
                    selectFile(e.dataTransfer.files[0]);
                  }}
                >
                  <Upload size={27} />
                  <strong>{file ? file.name : "Drop an ISO here"}</strong>
                  <span>
                    {file
                      ? bytes(file.size)
                      : "or choose a file from your computer"}
                  </span>
                  <input
                    aria-label="Choose ISO file"
                    type="file"
                    accept=".iso"
                    onChange={(e) => selectFile(e.target.files?.[0])}
                  />
                </div>
                <p className="help">
                  Uploads are subject to the server’s size limit. For large
                  ISOs, use a file already on mounted storage.
                </p>
              </>
            )}
          </fieldset>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-footer">
            <button type="button" disabled={busy} onClick={onClose}>
              Cancel
            </button>
            <button
              className="primary"
              disabled={busy || !sid || (mode === "upload" && !file)}
            >
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <ArrowRight size={16} />
              )}{" "}
              {busy
                ? "Submitting…"
                : mode === "upload"
                  ? "Upload & analyze"
                  : "Analyze ISO"}
            </button>
          </div>
        </form>
      ) : (
        <Empty
          icon={Database}
          title="Add storage first"
          action={
            <button className="primary" onClick={onStorage}>
              Open storage <ArrowRight size={15} />
            </button>
          }
        >
          Register a mounted location so the appliance can find your ISO.
        </Empty>
      )}
    </dialog>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
