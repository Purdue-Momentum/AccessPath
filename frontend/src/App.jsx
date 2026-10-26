import { Route, Routes } from "react-router-dom";

function Home() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3">
      <h1 className="text-3xl font-semibold text-gray-900">AccessPath</h1>
      <p className="text-gray-500">Your starting point. Build from here.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  );
}
