import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";

function EditIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
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
function ChevronLeft() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
    </svg>
  );
}
function ChevronRight() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  );
}

const initialEquationText = `Six molecules of carbon dioxide and six molecules of water, with light energy, produce one molecule of glucose and six molecules of oxygen.`;
const initialFigureText = `Line graph of photosynthesis rate against light intensity. The rate increases as light intensity rises, then levels off at high intensity as another factor becomes limiting.`;

export default function ReviewEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [equationText, setEquationText] = useState(initialEquationText);
  const [figureText, setFigureText] = useState(initialFigureText);
  const [activeSection, setActiveSection] = useState("equation");
  const [reviewerComment, setReviewerComment] = useState(
    "Reviewed complete draft and both piece checks. Approved v2 for student access."
  );
  const [approved, setApproved] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleApprove = () => {
    setApproved(true);
    setTimeout(() => navigate(`/approved/${id || "week4-photosynthesis"}`), 800);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Sub-header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-white px-6 py-3">
        <div className="text-xs text-blue-700 font-medium mb-1">BIOL 11000 · Fundamentals of Biology</div>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Review accessible draft</h1>
            <p className="text-xs text-gray-500">
              Week 4 — Photosynthesis · BIOL 11000 · Draft v2 · Oct 17, 2026, 09:42 EDT
            </p>
          </div>
          <span className="rounded-full border border-yellow-300 bg-yellow-50 px-3 py-1 text-xs font-semibold text-yellow-800">
            Awaiting final approval
          </span>
        </div>
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-gray-500">Reviewing as [Instructor name] · Edited by [TA name]</p>
          <p className="text-xs text-gray-400">
            {saved ? "✓ All changes saved" : "All changes saved · 09:38 EDT"}
          </p>
        </div>
      </div>

      {/* Three-column editor */}
      <div className="flex flex-1 min-h-0 gap-0">
        {/* Left: Original file */}
        <div className="w-72 flex-shrink-0 border-r border-gray-200 overflow-y-auto p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-900">Original file</h2>
            <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">Read only</span>
          </div>
          <p className="text-xs text-gray-500 mb-4">Week_04_Photosynthesis.pdf · Pages 5–6 of 12</p>

          {/* Original content */}
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
            <h3 className="font-bold text-gray-900 mb-2">Photosynthesis: converting light to energy</h3>
            <p className="text-gray-700 text-xs mb-4">
              Light energy drives the conversion of carbon dioxide and water into glucose and oxygen.
            </p>

            {/* Equation */}
            <div className="rounded border border-gray-200 bg-white p-3 mb-3">
              <div className="text-xs text-blue-700 font-medium mb-1">Equation 1 · Page 5</div>
              <div className="text-sm font-mono font-semibold leading-relaxed">
                6CO₂ + 6H₂O + light →<br />C₆H₁₂O₆ + 6O₂
              </div>
            </div>
            <p className="text-xs text-gray-500 mb-4">Equation 1. Overall reaction of photosynthesis.</p>

            {/* Figure */}
            <div className="rounded border border-gray-200 bg-white p-3 mb-3">
              <div className="text-xs text-blue-700 font-medium mb-1">Figure 2 · Page 6</div>
              {/* Simple SVG chart */}
              <svg width="100%" height="70" viewBox="0 0 200 70">
                <line x1="20" y1="60" x2="20" y2="5" stroke="#9ca3af" strokeWidth="1" />
                <line x1="20" y1="60" x2="190" y2="60" stroke="#9ca3af" strokeWidth="1" />
                <path d="M 20 55 Q 80 10 130 12 L 185 12" fill="none" stroke="#1d4ed8" strokeWidth="2" />
                <text x="5" y="35" fontSize="8" fill="#6b7280" transform="rotate(-90, 10, 35)">Rate of photosynthesis</text>
                <text x="100" y="70" fontSize="8" fill="#6b7280" textAnchor="middle">Light intensity →</text>
              </svg>
            </div>
            <p className="text-xs text-gray-500">Figure 2. Rate of photosynthesis at increasing light intensity.</p>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-xs text-blue-700">
            <button className="flex items-center gap-1 hover:underline"><ChevronLeft /> Previous page</button>
            <span className="text-gray-500">Page 5–6</span>
            <button className="flex items-center gap-1 hover:underline">Next <ChevronRight /></button>
          </div>
        </div>

        {/* Middle: Accessible draft editor */}
        <div className="flex-1 min-w-0 border-r border-gray-200 overflow-y-auto p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-900">Accessible draft · v2</h2>
            <button className="text-blue-600 hover:text-blue-800">
              <EditIcon />
            </button>
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-2 mb-4 text-sm text-gray-600 border-b border-gray-100 pb-2">
            <select className="text-xs border border-gray-200 rounded px-1 py-0.5 bg-white">
              <option>Heading 2</option>
              <option>Heading 1</option>
              <option>Heading 3</option>
              <option>Paragraph</option>
            </select>
            <button className="font-bold px-1.5 rounded hover:bg-gray-100">B</button>
            <button className="italic px-1.5 rounded hover:bg-gray-100">I</button>
            <button className="px-1.5 rounded hover:bg-gray-100">Link</button>
            <button className="px-1.5 rounded hover:bg-gray-100">List</button>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50/30 p-4 mb-4">
            <h3 className="font-bold text-gray-900 mb-3">Photosynthesis: converting light to energy</h3>

            {/* Equation section */}
            <div
              className={`mb-4 p-3 rounded-lg border cursor-pointer transition-colors ${
                activeSection === "equation" ? "border-blue-400 bg-white shadow-sm" : "border-gray-200 bg-white hover:border-blue-300"
              }`}
              onClick={() => setActiveSection("equation")}
            >
              <div className="text-xs text-blue-700 font-medium mb-1">Equation 1 · Spoken description</div>
              <textarea
                value={equationText}
                onChange={(e) => setEquationText(e.target.value)}
                className="w-full text-sm text-gray-800 bg-transparent border-none resize-none focus:outline-none"
                rows={3}
                onClick={(e) => e.stopPropagation()}
              />
            </div>

            {/* Figure section */}
            <div
              className={`mb-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                activeSection === "figure" ? "border-blue-400 bg-white shadow-sm" : "border-gray-200 bg-white hover:border-blue-300"
              }`}
              onClick={() => setActiveSection("figure")}
            >
              <div className="text-xs text-blue-700 font-medium mb-1">Figure 2 · Alternative text</div>
              <textarea
                value={figureText}
                onChange={(e) => setFigureText(e.target.value)}
                className="w-full text-sm text-gray-800 bg-transparent border-none resize-none focus:outline-none"
                rows={3}
                onClick={(e) => e.stopPropagation()}
              />
              <div className="text-xs text-gray-400 mt-1">Edited by TA Name · 09:38 EDT</div>
            </div>
          </div>

          <p className="text-xs text-gray-400 mb-4">Editable text · Changes are recorded in version history.</p>
          <button
            onClick={handleSave}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            {saved ? "Saved ✓" : "Save changes"}
          </button>
        </div>

        {/* Right: Suggestions & approval */}
        <div className="w-72 flex-shrink-0 overflow-y-auto p-5">
          <div className="flex items-center gap-3 mb-4">
            <button className="text-sm font-semibold text-blue-700 border-b-2 border-blue-700 pb-0.5">Suggestions</button>
            <button className="text-sm text-gray-500 hover:text-gray-700">History</button>
          </div>

          {/* Piece checks */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">Piece checks · 2 of 2 complete</h3>
            </div>
            <div className="flex flex-col gap-1 text-xs text-gray-700 mb-2">
              <div className="flex items-center gap-1.5 text-green-700">
                <CheckIcon /> <span>Equation 1 · Oxygen narration verified</span>
              </div>
              <div className="flex items-center gap-1.5 text-green-700">
                <CheckIcon /> <span>Figure 2 · Trend and plateau described</span>
              </div>
            </div>
            <div className="text-xs text-gray-400">Checked by TA Name · 09:38 EDT</div>
          </div>

          {/* AI suggestion */}
          <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 mb-5">
            <div className="text-xs font-semibold text-blue-800 mb-1">AI suggestion · Applied</div>
            <p className="text-xs text-gray-700">
              Use heading levels consistently so readers can navigate by section.
            </p>
            <Link to={`/audit/${id || "week4-photosynthesis"}`} className="text-xs text-blue-700 hover:underline mt-1 block">
              View revision v1 → v2
            </Link>
          </div>

          {/* Final reviewer */}
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Final reviewer: Professor Name</h3>
            <label className="flex items-start gap-2 mb-3 cursor-pointer">
              <input type="checkbox" defaultChecked className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-700" />
              <span className="text-xs text-gray-700">
                I reviewed the source, accessible text, and piece checks for this course.
              </span>
            </label>
            <div className="text-xs font-medium text-gray-700 mb-1">Comments:</div>
            <textarea
              value={reviewerComment}
              onChange={(e) => setReviewerComment(e.target.value)}
              rows={3}
              className="w-full rounded border border-gray-200 px-3 py-2 text-xs text-gray-700 mb-3 focus:border-blue-400 focus:outline-none resize-none"
            />
            <div className="flex flex-col gap-2">
              <button
                onClick={handleApprove}
                className={`flex items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition-colors w-full ${
                  approved ? "bg-green-600" : "bg-blue-900 hover:bg-blue-800"
                }`}
              >
                <CheckIcon /> {approved ? "Approved!" : "Approve & publish"}
              </button>
              <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors w-full">
                Disapprove / flag errors
              </button>
              <button className="flex items-center justify-center gap-1.5 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors w-full">
                <RefreshIcon /> Regenerate draft
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
