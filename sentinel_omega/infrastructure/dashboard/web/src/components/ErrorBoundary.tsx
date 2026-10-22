/**
 * ErrorBoundary: atrapa errores de render en las pestañas.
 * Sin esto, un componente que crashea deja TODA la pantalla vacía.
 */
import React from "react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[ErrorBoundary]", error.message, errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-500/10">
          <p className="text-sm font-bold text-red-400">Error en este componente</p>
          <p className="mt-1 text-xs text-red-300/80">{this.state.error?.message}</p>
          <button
            className="mt-2 px-3 py-1 text-xs rounded bg-surface-sunken border border-border hover:bg-surface"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Reintentar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
