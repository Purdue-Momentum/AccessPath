import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";

function CheckIcon({ done }) {
  if (done)
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} className="text-blue-700 flex-shrink-0">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    );
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-gray-400 flex-shrink-0">
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="text-blue-600 animate-spin flex-shrink-0">
      <path strokeLinecap="round" d="M12 3a9 9 0 110 18" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-blue-700">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
    </svg>
  );
}

const steps = [
  { id: "extract", label: "Original saved & text extracted", detail: "12 of 12 pages complete" },
  { id: "headings", label: "Headings & reading order", detail: "Structure drafted" },
  { id: "figures", label: "Figures & equations", detail: "Equation 1 needs context" },
  { id: "assemble", label: "Assemble draft for human review", detail: "Not started" },
];

const activityLog = [
  { time: "09:12:06 EDT", msg: "Paused on Equation 1, page 5." },
  { time: "09:11:48 EDT", msg: "Figure 2 trend description drafted." },
  { time: "09:11:20 EDT", msg: "Reading order extracted." },
  { time: "09:10:04 EDT", msg: "Original stored securely." },
];

export default function DraftProgress() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [contextAnswer, setContextAnswer] = useState("");

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="text-sm text-blue-700 font-medium mb-2">BIOL 11000 · Fundamentals of Biology</div>

      <h1 className="text-3xl font-bold text-gray-900 mb-1">Creating your accessible draft</h1>
      <p className="text-sm text-gray-500 mb-6">
        Week 4 — Photosynthesis · Draft v1 · Started by TA Name at 09:10 EDT
      </p>

      <div className="grid grid-cols-3 gap-5">
        {/* Main progress column */}
        <div className="col-span-2 flex flex-col gap-5">
          {/* Progress card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-3">
              <span className="rounded-full bg-yellow-100 text-yellow-800 text-xs font-semibold px-3 py-1">
                Paused · Needs your input
              </span>
              <span className="text-2xl font-bold text-blue-800">68%</span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-gray-200 rounded-full mb-4 overflow-hidden">
              <div className="h-full bg-blue-700 rounded-full" style={{ width: "68%" }} />
            </div>

            <p className="text-sm text-gray-600 mb-5">~2 minutes remaining</p>

            {/* Steps */}
            <div className="flex flex-col gap-3">
              {steps.map((step, i) => {
                const isDone = i < 2;
                const isActive = i === 2;
                const isWaiting = i > 2;
                return (
                  <div key={step.id} className="flex items-start gap-3">
                    {isDone ? <CheckIcon done /> : isActive ? <SpinnerIcon /> : <CheckIcon done={false} />}
                    <div>
                      <div className={`text-sm font-semibold ${isDone ? "text-gray-700" : isActive ? "text-blue-800" : "text-gray-400"}`}>
                        {step.label}
                      </div>
                      <div className="text-xs text-gray-500">{step.detail}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Context needed card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Context needed: Equation 1</h2>
              <span className="text-xs text-gray-500 bg-gray-100 rounded px-2 py-0.5">Page 5</span>
            </div>

            {/* Equation display */}
            <div className="rounded-lg bg-gray-50 border border-gray-200 p-4 mb-4">
              <div className="text-xs text-blue-700 font-medium mb-2">Equation 1 · Page 5</div>
              <div className="text-lg font-semibold text-gray-900 font-mono leading-relaxed">
                6CO₂ + 6H₂O + light →
                <br />
                C₆H₁₂O₆ + 6O₂
              </div>
            </div>

            <p className="text-sm text-gray-700 mb-4">
              The oxygen subscript is unclear in the scan. Does the product read "6O₂" (six oxygen molecules)?
            </p>

            <textarea
              value={contextAnswer}
              onChange={(e) => setContextAnswer(e.target.value)}
              placeholder="Type your answer here…"
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-700 mb-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
              rows={2}
            />

            <div className="flex gap-3">
              <button
                onClick={() => navigate(`/review/week4-photosynthesis`)}
                className="rounded-lg bg-blue-900 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                Add context &amp; resume
              </button>
              <button
                onClick={() => navigate(`/review/week4-photosynthesis`)}
                className="rounded-lg border border-gray-300 px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Continue; flag for review
              </button>
            </div>
          </div>
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-5">
          {/* Document info */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="font-semibold text-gray-900 mb-2">Week 4 — Photosynthesis</h3>
            <p className="text-xs text-gray-500 mb-1">BIOL 11000 · Instructor Name</p>
            <p className="text-xs text-gray-500 mb-4">Week_04_Photosynthesis.pdf · 12 pages · 4.8 MB</p>

            <div className="flex items-start gap-2 mb-2">
              <ShieldIcon />
              <div>
                <div className="text-sm font-semibold text-gray-800 leading-tight">Original safely retained</div>
                <p className="text-xs text-gray-500 mt-1">
                  Conversion never overwrites your source. You can leave this page and return from course documents.
                </p>
              </div>
            </div>

            <button className="text-xs text-blue-700 hover:underline mt-2">View original →</button>
            <p className="text-xs text-gray-400 mt-2">Last update · 09:12:06 EDT</p>
          </div>

          {/* Live activity */}
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Live activity</h3>
            <div className="flex flex-col gap-3">
              {activityLog.map((item, i) => (
                <div key={i}>
                  <div className="text-xs font-semibold text-blue-700">{item.time}</div>
                  <div className="text-xs text-gray-600">{item.msg}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
