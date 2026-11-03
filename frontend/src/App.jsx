import { Navigate, Route, Routes } from "react-router-dom";
import Shell from "./components/Shell.jsx";
import ReviewShell from "./components/ReviewShell.jsx";
import CourseDocuments from "./pages/CourseDocuments.jsx";
import DocumentDetail from "./pages/DocumentDetail.jsx";
import Upload from "./pages/Upload.jsx";
import DraftProgress from "./pages/DraftProgress.jsx";
import ReviewEditor from "./pages/ReviewEditor.jsx";
import ApprovedPublished from "./pages/ApprovedPublished.jsx";
import AuditLog from "./pages/AuditLog.jsx";
import HumanReviewQueue from "./pages/HumanReviewQueue.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/documents" replace />} />

      <Route path="/documents" element={<Shell><CourseDocuments /></Shell>} />
      <Route path="/document/:id" element={<Shell><DocumentDetail /></Shell>} />
      <Route path="/upload" element={<Shell><Upload /></Shell>} />
      <Route path="/draft-progress/:id" element={<Shell><DraftProgress /></Shell>} />
      <Route path="/approved/:id" element={<Shell><ApprovedPublished /></Shell>} />
      <Route path="/audit/:id" element={<Shell><AuditLog /></Shell>} />
      <Route path="/audit-history" element={<Shell><AuditLog /></Shell>} />
      <Route path="/review-queue" element={<Shell><HumanReviewQueue /></Shell>} />

      {/* Review editor has its own shell (no sidebar, full-height 3-col layout) */}
      <Route path="/review/:id" element={<ReviewShell><ReviewEditor /></ReviewShell>} />
    </Routes>
  );
}
