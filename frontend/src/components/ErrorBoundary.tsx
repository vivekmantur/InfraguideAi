import React from "react";

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: string }> {
  state = { error: "" };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : "The interface could not render this response." };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="min-h-screen bg-cloud p-6 text-ink">
          <section className="mx-auto max-w-3xl rounded-lg border border-red-200 bg-white p-5 shadow-panel">
            <h1 className="text-2xl font-semibold text-red-700">InfraGuide AI could not render the report</h1>
            <p className="mt-3 text-ink/70">{this.state.error}</p>
            <p className="mt-3 text-sm text-ink/60">Restart the frontend and backend after code changes, then generate the blueprint again.</p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
