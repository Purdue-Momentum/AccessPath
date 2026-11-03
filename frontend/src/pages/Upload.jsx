import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { courses } from "../data/demo.js";

function UploadAreaIcon() {
  return (
    <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-blue-400">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}
function SparklesIcon() {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
    </svg>
  );
}

export default function Upload() {
  const navigate = useNavigate();
  const [course, setCourse] = useState("");
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [context, setContext] = useState("");
  const [options, setOptions] = useState({
    figures: true,
    headings: true,
    video: true,
  });

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleFileInput = (e) => {
    const f = e.target.files[0];
    if (f) setFile(f);
  };

  const handleGenerate = () => {
    if (!course) return;
    navigate("/draft-progress/week4-photosynthesis");
  };

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Upload file(s)</h1>

      <div className="rounded-xl border border-gray-200 bg-white p-6 flex flex-col gap-5">
        {/* Course selector */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">Course</label>
          <div className="relative">
            <select
              value={course}
              onChange={(e) => setCourse(e.target.value)}
              className="w-full appearance-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 bg-white pr-8 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Name</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>{c.name} — {c.code}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-3 top-3 text-gray-400" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed py-10 cursor-pointer transition-colors ${
            dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-gray-50 hover:border-blue-300 hover:bg-blue-50/30"
          }`}
          onClick={() => document.getElementById("file-input").click()}
        >
          <input id="file-input" type="file" className="hidden" accept=".docx,.pptx,.pdf,.mp4" onChange={handleFileInput} />
          <UploadAreaIcon />
          {file ? (
            <p className="mt-2 text-sm font-semibold text-blue-700">{file.name}</p>
          ) : (
            <p className="mt-2 text-sm font-semibold text-blue-700">Upload File Here</p>
          )}
        </div>
        <p className="text-xs text-gray-500 -mt-3">Accepted file types: .docx, .pptx, .pdf, .mp4 · Maximum 250 MB</p>

        {/* Context */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Context <span className="font-normal text-gray-400">· optional</span>
          </label>
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            placeholder="Add any notes to help the AI generate a better accessible draft…"
          />
        </div>

        {/* Conversion options */}
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-2">Conversion options</div>
          <div className="flex flex-col gap-2">
            {[
              { key: "figures", label: "Include figure descriptions and equation narration" },
              { key: "headings", label: "Preserve headings and reading order" },
              { key: "video", label: "Create a video transcript when media is present" },
            ].map(({ key, label }) => (
              <label key={key} className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options[key]}
                  onChange={(e) => setOptions((o) => ({ ...o, [key]: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-blue-700 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-between pt-2">
          <button
            onClick={() => navigate("/documents")}
            className="rounded-lg border border-gray-300 px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleGenerate}
            className="flex items-center gap-2 rounded-lg bg-blue-900 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors disabled:opacity-50"
          >
            <SparklesIcon />
            Generate draft
          </button>
        </div>
      </div>
    </div>
  );
}
