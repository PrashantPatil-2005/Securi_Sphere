export default function DemoCenterPage() {
  return (
    <main className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">SecuriSphere Demo Center</h1>
        <p className="text-sm text-muted">
          The interactive simulation center is temporarily unavailable while we improve its reliability.
        </p>
      </header>

      <section className="space-y-4 rounded-lg border border-border-subtle p-6">
        <div>
          <h2 className="text-lg font-medium">Security Monitoring Dashboard</h2>
          <p className="mt-2 text-sm text-muted">
            Access available hosts, security alerts, and investigation tools through the main dashboard.
          </p>
        </div>
        <a href="/dashboard" className="btn-primary inline-flex items-center">
          Return to Dashboard
        </a>
      </section>
    </main>
  );
}