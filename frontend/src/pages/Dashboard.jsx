/**
 * Dashboard — minimal placeholder landing page.
 * Exists so that a successful login has somewhere to redirect to and you can
 * visually confirm the session works. Replace with the real app shell later.
 */
export default function Dashboard() {
  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center bg-white px-6 text-center">
      <h1 className="text-3xl font-semibold text-gray-900">You're signed in</h1>
      <p className="mt-3 text-sm text-gray-600">
        This is a placeholder page to confirm login works.
      </p>
    </div>
  );
}
