import { Link, useSearchParams } from "react-router-dom";
import { documents, courses } from "../data/demo.js";

function StatusBadge({ status }) {
  const map = {
    published: { label: "Published", cls: "bg-blue-100 text-blue-800" },
    awaiting_review: { label: "Awaiting review", cls: "bg-yellow-100 text-yellow-800" },
    flagged: { label: "Flagged", cls: "bg-red-100 text-red-800" },
    draft: { label: "Draft", cls: "bg-gray-100 text-gray-700" },
  };
  const { label, cls } = map[status] || map.draft;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function UploadIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12M8 8l4-4 4 4" />
    </svg>
  );
}

export default function CourseDocuments() {
  const [params] = useSearchParams();
  const courseId = params.get("course") || "biol11000";
  const course = courses.find((c) => c.id === courseId) || courses[0];
  const docs = documents.filter((d) => d.courseId === courseId);

  const published = docs.filter((d) => d.status === "published").length;
  const awaitingReview = docs.filter((d) => d.status === "awaiting_review").length;

  const actionLabel = (status) => {
    if (status === "published") return "Open →";
    if (status === "awaiting_review") return "Review →";
    if (status === "flagged") return "Resolve →";
    return "Open →";
  };

  const actionTo = (doc) => {
    if (doc.status === "awaiting_review") return `/review/${doc.id}`;
    return `/document/${doc.id}`;
  };

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-sm text-blue-700 font-medium mb-2">
        Instructor workspace · Fall 2026
      </div>

      <div className="flex items-start justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Course documents</h1>
        <Link
          to="/upload"
          className="flex items-center gap-2 rounded-lg bg-blue-900 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
        >
          <UploadIcon />
          Upload document
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="text-4xl font-bold text-gray-900">{docs.length}</div>
          <div className="text-sm text-gray-500 mt-1">Course documents</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="text-4xl font-bold text-gray-900">{awaitingReview + 1}</div>
          <div className="text-sm text-gray-500 mt-1">Items awaiting review</div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="text-4xl font-bold text-gray-900">{published}</div>
          <div className="text-sm text-gray-500 mt-1">Published &amp; monitored</div>
        </div>
      </div>

      {/* Course section */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">{course.name}</h2>
          <div className="text-sm text-gray-500">{course.code} · Instructor Name · TA Name</div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
            All statuses
          </button>
          <button className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
            All types
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-5 py-3 font-semibold text-gray-600">Document &amp; stored versions</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Reviewer</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Updated</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Audit Log</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-600">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {docs.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-4">
                  <div className="font-semibold text-gray-900">{doc.title}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{doc.fileType} · {doc.accessibleVersion}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <button className="text-xs text-blue-700 hover:underline">Original retained</button>
                    <span className="text-gray-300">·</span>
                    <button className="text-xs text-blue-700 hover:underline">View versions</button>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-4 py-4 text-gray-700">{doc.reviewerName}</td>
                <td className="px-4 py-4 text-gray-600 text-xs">{doc.updatedAt}</td>
                <td className="px-4 py-4">
                  <Link to={`/audit/${doc.id}`} className="text-blue-700 hover:underline text-xs font-medium">
                    Audit log
                  </Link>
                </td>
                <td className="px-4 py-4">
                  <Link
                    to={actionTo(doc)}
                    className="text-blue-700 hover:underline text-sm font-medium"
                  >
                    {actionLabel(doc.status)}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          <span>Showing {docs.length} of {course.documentCount} documents in this course</span>
          <div className="flex gap-4">
            <Link to="/review-queue" className="text-blue-700 hover:underline">View review queue →</Link>
            <Link to="/audit-history" className="text-blue-700 hover:underline">View audit history →</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
