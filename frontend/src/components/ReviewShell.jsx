import { Link, useNavigate } from "react-router-dom";

function LogoMark() {
  return (
    <img src="/logo.png" alt="AccessPath logo" className="h-9 w-9 flex-shrink-0" />
  );
}

export default function ReviewShell({ children }) {
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Top nav */}
      <header className="flex h-14 items-center gap-4 border-b border-gray-200 px-6 flex-shrink-0">
        <Link to="/" className="flex items-center gap-2 mr-4">
          <LogoMark />
          <span className="text-xl font-bold text-blue-900 tracking-tight">AccessPath</span>
        </Link>

        <button
          onClick={() => navigate("/documents")}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to documents
        </button>

        <div className="ml-auto flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm font-semibold text-gray-900 leading-tight">Instructor Name</div>
            <div className="text-xs text-gray-500">University</div>
          </div>
          <div className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-gray-300 bg-gray-100 text-gray-600">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
        </div>
      </header>

      {/* Content fills remaining height */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {children}
      </div>
    </div>
  );
}
