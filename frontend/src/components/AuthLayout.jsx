/**
 * AuthLayout
 * Split-screen shell used by the Login and Sign Up pages.
 * Left: solid blue panel. Right: white panel that holds the form.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="flex h-full min-h-screen w-full">
      {/* Left blue panel */}
      <div className="hidden w-1/2 bg-blue-700 md:block" aria-hidden="true" />

      {/* Right white panel with the form */}
      <div className="flex w-full items-center justify-center bg-white px-6 py-12 md:w-1/2">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
