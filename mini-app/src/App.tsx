import { useEffect, useState } from "react";
import "./App.css";
import { getMe, type MeResponse } from "./api/client";
import { CreateJobPage } from "./pages/CreateJobPage";
import { EmployerJobsPage } from "./pages/EmployerJobsPage";
import { ProfilePage } from "./pages/ProfilePage";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        initDataUnsafe: { user?: { first_name?: string; username?: string } };
        ready: () => void;
        expand: () => void;
      };
    };
  }
}

type TelegramContext = {
  inTelegram: boolean;
  initData: string;
  userLabel: string;
};

type AppView = "profile" | "jobs" | "create";

type MeState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; me: MeResponse };

function readTelegramContext(): TelegramContext {
  const webApp = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;
  if (!webApp) {
    return { inTelegram: false, initData: "", userLabel: "гость" };
  }
  webApp.ready();
  webApp.expand();
  const user = webApp.initDataUnsafe?.user;
  const userLabel = user?.username
    ? `@${user.username}`
    : user?.first_name ?? "гость";
  return {
    inTelegram: true,
    initData: webApp.initData ?? "",
    userLabel,
  };
}

function isEmployerRole(role: MeResponse["role"]): boolean {
  return role === "employer" || role === "both";
}

function isWorkerRole(role: MeResponse["role"]): boolean {
  return role === "worker" || role === "both";
}

function App() {
  const [telegram] = useState(readTelegramContext);
  const [meState, setMeState] = useState<MeState>({ status: "loading" });
  const [view, setView] = useState<AppView>("profile");
  const [jobsReloadKey, setJobsReloadKey] = useState(0);

  useEffect(() => {
    if (!telegram.inTelegram || !telegram.initData) {
      return;
    }

    let cancelled = false;
    void getMe(telegram.initData)
      .then((me) => {
        if (cancelled) {
          return;
        }
        setMeState({ status: "ready", me });
        if (isEmployerRole(me.role)) {
          setView("jobs");
        } else {
          setView("profile");
        }
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Не удалось загрузить профиль";
        setMeState({ status: "error", message });
      });

    return () => {
      cancelled = true;
    };
  }, [telegram.inTelegram, telegram.initData]);

  function handleJobCreated() {
    setJobsReloadKey((k) => k + 1);
    setView("jobs");
  }

  function renderContent() {
    if (!telegram.inTelegram || !telegram.initData) {
      return (
        <section className="card">
          <p>
            {telegram.inTelegram
              ? "Нет initData — откройте приложение через синюю кнопку бота."
              : "Откройте через бота (WebApp) для просмотра профиля."}
          </p>
        </section>
      );
    }

    if (meState.status === "loading") {
      return <p className="status">Загрузка…</p>;
    }

    if (meState.status === "error") {
      return (
        <section className="card">
          <p className="error">{meState.message}</p>
        </section>
      );
    }

    const { me } = meState;
    const showEmployer = isEmployerRole(me.role);
    const showWorker = isWorkerRole(me.role);

    if (view === "create" && showEmployer) {
      return (
        <CreateJobPage
          initData={telegram.initData}
          onCreated={handleJobCreated}
          onCancel={() => setView("jobs")}
        />
      );
    }

    if (view === "jobs" && showEmployer) {
      return (
        <EmployerJobsPage
          initData={telegram.initData}
          reloadKey={jobsReloadKey}
          onCreateClick={() => setView("create")}
        />
      );
    }

    if (view === "profile" && showWorker) {
      return <ProfilePage initData={telegram.initData} />;
    }

    if (showEmployer) {
      return (
        <EmployerJobsPage
          initData={telegram.initData}
          reloadKey={jobsReloadKey}
          onCreateClick={() => setView("create")}
        />
      );
    }

    return <ProfilePage initData={telegram.initData} />;
  }

  const showNav =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    (isEmployerRole(meState.me.role) || isWorkerRole(meState.me.role));

  const navItems: { id: AppView; label: string; visible: boolean }[] =
    meState.status === "ready"
      ? [
          { id: "profile", label: "Профиль", visible: isWorkerRole(meState.me.role) },
          { id: "jobs", label: "Заявки", visible: isEmployerRole(meState.me.role) },
          { id: "create", label: "Создать", visible: isEmployerRole(meState.me.role) },
        ]
      : [];

  return (
    <main className="app">
      <h1>OutstaffingBot</h1>
      <p className="subtitle">
        {telegram.inTelegram ? `Telegram: ${telegram.userLabel}` : "Telegram Mini App"}
      </p>

      {showNav && navItems.filter((item) => item.visible).length > 1 ? (
        <nav className="app-nav">
          {navItems
            .filter((item) => item.visible)
            .map((item) => (
              <button
                key={item.id}
                type="button"
                className={`nav-btn${view === item.id ? " active" : ""}`}
                onClick={() => setView(item.id)}
              >
                {item.label}
              </button>
            ))}
        </nav>
      ) : null}

      {renderContent()}
    </main>
  );
}

export default App;
