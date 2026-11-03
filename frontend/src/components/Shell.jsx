import { Link, useLocation, useNavigate } from "react-router-dom";
import { courses } from "../data/demo.js";

// ── icons (inline SVG kept small) ──────────────────────────────────────────
function UploadIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12M8 8l4-4 4 4" />
    </svg>
  );
}
function DocsIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7h18M3 12h18M3 17h12" />
    </svg>
  );
}
function QueueIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  );
}
function AuditIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
function ChevronDown() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}
function UserIcon() {
  return (
    <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
    </svg>
  );
}

// AccessPath logo mark
function LogoMark() {
  return (
    <img src="/logo.png" alt="AccessPath logo" className="h-9 w-9 flex-shrink-0" />
  );
}

export default function Shell({ children }) {
  const location = useLocation();
  const navigate = useNavigate();

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + "/");

  const navItem = (to, icon, label) => (
    <Link
      to={to}
      className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        isActive(to)
          ? "bg-blue-50 text-blue-800"
          : "text-gray-700 hover:bg-gray-100"
      }`}
    >
      <span className={isActive(to) ? "text-blue-700" : "text-gray-500"}>{icon}</span>
      {label}
    </Link>
  );

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Top nav */}
      <header className="flex h-14 items-center gap-4 border-b border-gray-200 px-6 flex-shrink-0">
        <Link to="/" className="flex items-center gap-2 mr-4">
          <LogoMark />
          <span className="text-xl font-bold text-blue-900 tracking-tight">AccessPath</span>
        </Link>

        {/* Search */}
        <div className="flex-1 max-w-md">
          <div className="flex items-center gap-2 rounded-full border border-gray-300 bg-gray-50 px-4 py-1.5 text-sm text-gray-500">
            <SearchIcon />
            Search documents
          </div>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm font-semibold text-gray-900 leading-tight">Instructor Name</div>
            <div className="text-xs text-gray-500">University</div>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-gray-300 bg-gray-100 text-gray-600">
            <UserIcon />
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <aside className="w-52 flex-shrink-0 border-r border-gray-200 flex flex-col py-4 px-3 gap-1 overflow-y-auto">
          {navItem("/upload", <UploadIcon />, "Upload new")}
          {navItem("/documents", <DocsIcon />, "All documents")}
          {navItem("/review-queue", <QueueIcon />, "Human review queue")}
          {navItem("/audit-history", <AuditIcon />, "Audit history")}

          <div className="mt-4 px-3 pt-3 border-t border-gray-100">
            <button className="flex items-center justify-between w-full text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              All courses <ChevronDown />
            </button>
            <div className="flex flex-col gap-1">
              {courses.map((c) => (
                <Link
                  key={c.id}
                  to={`/documents?course=${c.id}`}
                  className={`rounded-lg px-2 py-2 transition-colors ${
                    location.search.includes(c.id) || (!location.search && c.id === "biol11000" && location.pathname === "/documents")
                      ? "bg-blue-50 border border-blue-200"
                      : "hover:bg-gray-50"
                  }`}
                >
                  <div className="text-sm font-semibold text-gray-900 leading-tight">{c.name}</div>
                  <div className="text-xs text-gray-500">{c.code} · {c.documentCount} documents</div>
                </Link>
              ))}
            </div>
          </div>

          <div className="mt-auto px-3 pt-3 text-xs text-gray-400">Fall 2026</div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
