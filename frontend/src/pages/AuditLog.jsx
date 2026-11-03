import { useParams } from "react-router-dom";
import { auditLog, eventColors } from "../data/demo.js";

function DownloadIcon() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12M8 12l4 4 4-4" />
    </svg>
  );
}

export default function AuditLog() {
  const { id } = useParams();

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-sm text-blue-700 font-medium mb-2">BIOL 11000 · Fundamentals of Biology</div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Document audit log</h1>
          <p className="text-sm text-gray-500 mt-1">Week 4 — Photosynthesis · BIOL 11000</p>
        </div>
        <button className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          <DownloadIcon /> Export audit log
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-5 py-3 font-semibold text-gray-600">Time / event</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Actor / responsibility</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Version</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Comments</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {auditLog.map((entry, i) => (
              <tr key={i} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-4 align-top">
                  <div className="font-medium text-gray-700 text-xs">{entry.time}</div>
                  <div className={`text-xs font-semibold mt-0.5 ${eventColors[entry.event] || "text-gray-600"}`}>
                    {entry.event}
                  </div>
                </td>
                <td className="px-4 py-4 align-top">
                  <div className="font-medium text-gray-800 text-xs">{entry.actor}</div>
                  <div className="text-xs text-gray-500">{entry.role}</div>
                </td>
                <td className="px-4 py-4 align-top">
                  <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {entry.version}
                  </span>
                </td>
                <td className="px-4 py-4 align-top text-xs text-gray-700 max-w-xs">
                  {entry.comment}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-t border-gray-200">
          <span className="text-xs text-gray-500">Published version: v2.</span>
          <div className="flex gap-3">
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              Compare v1 → v2
            </button>
            <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              View original
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
