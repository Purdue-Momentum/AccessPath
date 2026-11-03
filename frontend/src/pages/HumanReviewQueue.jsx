import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { reviewQueueItems } from "../data/demo.js";

function EquationIcon() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 text-blue-700 flex-shrink-0">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16M4 12h10M4 17h7" />
        <text x="18" y="19" fontSize="8" fill="currentColor" stroke="none">Σ</text>
      </svg>
    </div>
  );
}
function FigureIcon() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-gray-600 flex-shrink-0">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4v16" />
      </svg>
    </div>
  );
}
function VideoIcon() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-gray-600 flex-shrink-0">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.277A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
      </svg>
    </div>
  );
}
function ImageFlagIcon() {
  return (
    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-100 text-red-600 flex-shrink-0">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18M3 7l9-4 9 4v10l-9 4-9-4V7z" />
      </svg>
    </div>
  );
}
function FilterChip({ label }) {
  return (
    <button className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors">
      <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
      {label}
    </button>
  );
}
function InfoIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} className="text-blue-600">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

const iconMap = {
  equation: <EquationIcon />,
  figure: <FigureIcon />,
  video: <VideoIcon />,
};

function StatusBadge({ status }) {
  if (status === "awaiting_review")
    return <span className="rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">Awaiting review</span>;
  if (status === "flagged")
    return <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">Flagged</span>;
  return null;
}

export default function HumanReviewQueue() {
  const navigate = useNavigate();
  const [items] = useState(reviewQueueItems);

  const awaitingCount = items.filter((i) => i.status === "awaiting_review").length;
  const flaggedCount = items.filter((i) => i.status === "flagged").length;

  const getIcon = (item) => {
    if (item.status === "flagged") return <ImageFlagIcon />;
    return iconMap[item.icon] || <FigureIcon />;
  };

  const handleAction = (item) => {
    navigate(`/review/week4-photosynthesis`);
  };

  const buttonStyle = (item) => {
    const first = item.id === "eq1";
    const base = "rounded-lg px-4 py-2 text-sm font-semibold transition-colors whitespace-nowrap";
    if (first) return `${base} bg-blue-900 text-white hover:bg-blue-800`;
    return `${base} border border-gray-300 text-gray-700 hover:bg-gray-50`;
  };

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-xs text-blue-700 font-medium mb-2">
        Instructor workspace · Oct 17, 2026 · 09:18 EDT
      </div>

      <h1 className="text-3xl font-bold text-gray-900 mb-1">Human review queue</h1>
      <p className="text-sm text-gray-500 mb-4">Review the pieces that need subject expertise.</p>

      {/* Stats tabs */}
      <div className="flex items-center gap-3 mb-4">
        <button className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
          {items.length} open review items
        </button>
        <button className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          {awaitingCount} awaiting review
        </button>
        <button className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          {flaggedCount} flagged
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6">
        <FilterChip label="Course: All courses" />
        <FilterChip label="Status: Open" />
        <FilterChip label="Type: All pieces" />
        <FilterChip label="Reviewer: All staff" />
      </div>

      {/* Queue items */}
      <div className="flex flex-col gap-3 mb-6">
        {items.map((item) => (
          <div key={item.id} className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 hover:border-gray-300 transition-colors">
            {getIcon(item)}
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-gray-900 text-sm">{item.title}</div>
              <div className="text-xs text-gray-500 mt-0.5">{item.location}</div>
              <div className="text-xs text-gray-600 mt-0.5">{item.description}</div>
            </div>
            <div className="flex flex-col items-end gap-1 min-w-max">
              <StatusBadge status={item.status} />
              <div className="text-xs text-gray-400">Assigned: {item.assignee}</div>
            </div>
            <button
              onClick={() => handleAction(item)}
              className={buttonStyle(item)}
            >
              {item.action}
            </button>
          </div>
        ))}
      </div>

      {/* Info note */}
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 mb-4">
        <div className="flex items-center gap-2 font-semibold text-blue-800 text-sm mb-1">
          <InfoIcon />
          Piece review does not publish a document
        </div>
        <p className="text-xs text-gray-600">
          Complete the figure, equation, and video checks, then review the full accessible draft. Prof. Elena Morris provides the final approval and publication signoff.
        </p>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>Showing all {items.length} open items · 3 documents · 1 course</span>
        <button className="text-blue-700 hover:underline">View course documents →</button>
      </div>
    </div>
  );
}
