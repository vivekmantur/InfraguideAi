import React from "react";

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: string }> {
  state = { error: "" };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : "The interface could not render this response." };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="error-page">
          <section className="error-panel">
            <h1 className="error-title">InfraGuide AI could not render the report</h1>
            <p className="error-message">{this.state.error}</p>
            <p className="error-hint">Restart the frontend and backend after code changes, then generate the blueprint again.</p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
