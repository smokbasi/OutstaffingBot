import { Component, type ErrorInfo, type ReactNode } from "react";

type ErrorBoundaryProps = {
  children: ReactNode;
};

type ErrorBoundaryState = {
  error: Error | null;
};

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Mini App render error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app">
          <section className="card">
            <h2>Ошибка приложения</h2>
            <p className="error">
              {this.state.error.message || "Не удалось отобразить экран. Закройте Mini App и откройте снова через бота."}
            </p>
            <button
              type="button"
              className="btn"
              onClick={() => this.setState({ error: null })}
            >
              Попробовать снова
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
