import { Link, useParams, useNavigate } from "react-router-dom";
import { documents } from "../data/demo.js";

function DownloadIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12M8 12l4 4 4-4" />
    </svg>
  );
}
function FileIcon() {
  return (
    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}
function HtmlIcon() {
  return (
    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  );
}
function EditIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}
function RefreshIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}

export default function DocumentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const doc = documents.find((d) => d.id === id) || documents[0];

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-sm text-blue-700 font-medium mb-2">
        BIOL 11000 · Fundamentals of Biology
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{doc.title}</h1>
          <div className="text-sm text-gray-500 mt-1">
            BIOL 11000 / Course materials / {doc.week} · Fall 2026
          </div>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
          Published · Monitor mode
        </span>
      </div>

      {/* Top row cards */}
      <div className="grid grid-cols-2 gap-5 mb-5">
        {/* Stored original */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-gray-500"><FileIcon /></span>
            <h2 className="font-semibold text-gray-900">Stored original</h2>
          </div>
          <div className="text-sm font-medium text-gray-900 mb-1">{doc.originalFile}</div>
          <div className="text-xs text-gray-500 mb-1">
            {doc.pages} pages · {doc.sizeMB} MB · Uploaded Oct 17, 09:10 EDT
          </div>
          <div className="text-xs text-gray-500 mb-4">Uploaded by TA Name · Retained unchanged</div>
          <div className="flex gap-3">
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              View original
            </button>
            <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <DownloadIcon /> Download PDF
            </button>
          </div>
        </div>

        {/* Accessible version */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-blue-600"><HtmlIcon /></span>
            <h2 className="font-semibold text-gray-900">Accessible version · v2</h2>
          </div>
          <div className="text-sm font-medium text-gray-900 mb-1">Week 4 — Photosynthesis.html</div>
          <div className="text-xs text-gray-500 mb-1">Published Oct 17, 2026 · 10:03 EDT</div>
          <div className="text-xs text-gray-500 mb-4">Approved by Instructor Name · 10:02 EDT</div>
          <div className="flex gap-3">
            <Link
              to={`/approved/${doc.id}`}
              className="rounded-lg bg-blue-900 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              Open published
            </Link>
            <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <DownloadIcon /> Download HTML
            </button>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-2 gap-5">
        {/* Document monitor */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Document monitor</h2>
            <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
              No open flags
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">Human review and maintenance continue after publication.</p>
          <dl className="text-sm space-y-2">
            <div className="flex gap-2">
              <dt className="w-36 text-gray-500 flex-shrink-0">Latest approval</dt>
              <dd className="text-gray-800">Instructor Name · Oct 17, 2026, 10:02 EDT</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-36 text-gray-500 flex-shrink-0">Piece review</dt>
              <dd className="text-gray-800">2 of 2 complete · Equation 1 and Figure 2</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-36 text-gray-500 flex-shrink-0">Last edited by</dt>
              <dd className="text-gray-800">TA Name · Oct 17, 2026, 09:38 EDT</dd>
            </div>
            <div className="flex gap-2">
              <dt className="w-36 text-gray-500 flex-shrink-0">Monitor state</dt>
              <dd className="text-gray-800">Active · Current published version remains v2</dd>
            </div>
          </dl>
          <Link
            to={`/audit/${doc.id}`}
            className="mt-4 inline-block text-xs text-blue-700 hover:underline"
          >
            View complete audit history →
          </Link>
        </div>

        {/* Update this document */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Update this document</h2>
          <div className="flex flex-col gap-3">
            <Link
              to={`/review/${doc.id}`}
              className="flex items-center gap-2 rounded-lg bg-blue-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors w-full justify-center"
            >
              <EditIcon /> Make edits
            </Link>
            <button className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors w-full justify-center">
              <RefreshIcon /> Regenerate AI draft
            </button>
            <p className="text-xs text-gray-500 text-center">New work creates draft v3</p>
          </div>
        </div>
      </div>
    </div>
  );
}
