import { StrictMode, Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

type EBState = { hasError: boolean; message: string };

class ErrorBoundary extends Component<{ children: ReactNode }, EBState> {
  state: EBState = { hasError: false, message: "" };

  static getDerivedStateFromError(error: unknown): EBState {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : String(error),
    };
  }

  componentDidCatch(error: unknown) {
    console.error("Dashboard runtime error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: "100vh", background: "#08090a", color: "#f7f8f8", padding: 24 }}>
          <h1 style={{ marginTop: 0 }}>Sentinel Omega Dashboard</h1>
          <p>La UI encontró un error en runtime (ya no debe quedarse en negro).</p>
          <pre style={{ whiteSpace: "pre-wrap", color: "#ffb4b4" }}>{this.state.message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("No se encontró #root en index.html");
}

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
