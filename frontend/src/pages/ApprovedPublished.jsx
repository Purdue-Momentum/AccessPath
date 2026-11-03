import { Link, useParams } from "react-router-dom";

function DownloadIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12M8 12l4 4 4-4" />
    </svg>
  );
}
function FileIcon() {
  return (
    <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-gray-400">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );
}

export default function ApprovedPublished() {
  const { id } = useParams();

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-sm text-blue-700 font-medium mb-2">BIOL 11000 · Fundamentals of Biology</div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Approved &amp; published</h1>
          <p className="text-sm text-gray-500 mt-1">Week 4 — Photosynthesis is available to your students.</p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
          Published · Monitor mode
        </span>
      </div>

      <div className="grid grid-cols-3 gap-5">
        {/* Left 2/3 */}
        <div className="col-span-2 flex flex-col gap-5">
          {/* Original file card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Original file</h2>
            <div className="flex items-start gap-3 mb-4">
              <FileIcon />
              <div>
                <div className="font-semibold text-gray-900">Week 4 — Photosynthesis</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  BIOL 11000 · Instructor Name · Uploaded Oct 17, 09:10 EDT
                </div>
                <div className="text-xs text-gray-500">Week_04_Photosynthesis.pdf · 12 pages · 4.8 MB</div>
              </div>
            </div>
            <div className="flex gap-3">
              <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                View original
              </button>
              <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                <DownloadIcon /> Download PDF
              </button>
            </div>
          </div>

          {/* Accessible HTML card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Accessible HTML · Version 2</h2>

            {/* Preview area */}
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 mb-5 min-h-32 flex items-center justify-center">
              <div className="text-sm text-gray-500">Preview of accessible version</div>
            </div>

            <div className="flex items-center gap-3">
              <button className="rounded-lg bg-blue-900 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                Open accessible version
              </button>
              <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                <DownloadIcon /> Download HTML
              </button>
            </div>
            <button className="mt-3 text-xs text-blue-700 hover:underline">Download original PDF →</button>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-5">
          {/* Human signoff */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Human signoff</h3>
            <div className="mb-4 pb-4 border-b border-gray-100">
              <div className="font-semibold text-gray-800 text-sm">Instructor Name</div>
              <div className="text-xs text-gray-500">Approver · Course instructor</div>
              <div className="text-xs text-gray-400 mt-1">Oct 17, 2026 · 10:02 EDT</div>
            </div>
            <div>
              <div className="font-semibold text-gray-800 text-sm">TA Name</div>
              <div className="text-xs text-gray-500">Editor · Teaching assistant</div>
              <div className="text-xs text-gray-400 mt-1">Equation narration and figure alt text edited at 09:38 EDT.</div>
            </div>
          </div>

          {/* Publish destination */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Publish destination</h3>
            <div className="text-sm text-gray-700 mb-1">BIOL 11000 / Fall 2026</div>
            <div className="text-xs text-gray-500 mb-1">Course materials / Week 4</div>
            <div className="text-xs text-gray-500 mb-3">Published by Prof. Elena Morris</div>
            <div className="text-xs text-gray-400 mb-3">Oct 17, 2026 · 10:03 EDT</div>
            <Link to={`/audit/${id || "week4-photosynthesis"}`} className="text-xs text-blue-700 hover:underline">
              View audit history →
            </Link>
          </div>

          {/* Monitor mode */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <span className="inline-block rounded-full bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 mb-3">
              Monitor mode active
            </span>
            <p className="text-xs text-gray-600 mb-3">
              Next staff review: Nov 17, 2026. You can edit or regenerate later without replacing this published version.
            </p>
            <Link to={`/document/${id || "week4-photosynthesis"}`} className="text-xs text-blue-700 hover:underline">
              Open document monitor →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
