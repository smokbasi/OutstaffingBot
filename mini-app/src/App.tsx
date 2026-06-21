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

type AppMode = "worker" | "employer";
type EmployerView = "jobs" | "create";

type MeState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; me: MeResponse };

const ROLE_STORAGE_KEY = "outstaffingbot:app-mode";

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

function hasWorkerAccess(role: MeResponse["role"]): boolean {
  return role === "worker" || role === "both";
}

function hasEmployerAccess(role: MeResponse["role"]): boolean {
  return role === "employer" || role === "both";
}

function needsRolePicker(role: MeResponse["role"]): boolean {
  return role === "both";
}

function resolveInitialMode(role: MeResponse["role"]): AppMode | null {
  if (role === "worker") {
    return "worker";
  }
  if (role === "employer") {
    return "employer";
  }
  if (typeof sessionStorage === "undefined") {
    return null;
  }
  const stored = sessionStorage.getItem(ROLE_STORAGE_KEY);
  if (stored === "worker" && hasWorkerAccess(role)) {
    return "worker";
  }
  if (stored === "employer" && hasEmployerAccess(role)) {
    return "employer";
  }
  return null;
}

function persistMode(mode: AppMode | null) {
  if (typeof sessionStorage === "undefined") {
    return;
  }
  if (mode === null) {
    sessionStorage.removeItem(ROLE_STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(ROLE_STORAGE_KEY, mode);
}

function RolePicker({
  onSelect,
}: {
  onSelect: (mode: AppMode) => void;
}) {
  return (
    <section className="card role-picker">
      <h2>Кто вы?</h2>
      <p className="hint">Выберите режим — профиль работника и заявки работодателя показываются отдельно.</p>
      <div className="role-cards">
        <button type="button" className="role-card" onClick={() => onSelect("worker")}>
          <span className="role-card-icon">👷</span>
          <span className="role-card-title">Я ищу работу</span>
          <span className="role-card-desc">Профиль, опыт и настройки для поиска смен</span>
        </button>
        <button type="button" className="role-card" onClick={() => onSelect("employer")}>
          <span className="role-card-icon">🏢</span>
          <span className="role-card-title">Я работодатель</span>
          <span className="role-card-desc">Заявки на персонал и создание новых смен</span>
        </button>
      </div>
    </section>
  );
}

function App() {
  const [telegram] = useState(readTelegramContext);
  const [meState, setMeState] = useState<MeState>({ status: "loading" });
  const [appMode, setAppMode] = useState<AppMode | null>(null);
  const [employerView, setEmployerView] = useState<EmployerView>("jobs");
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
        setAppMode(resolveInitialMode(me.role));
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

  function handleSelectMode(mode: AppMode) {
    setAppMode(mode);
    persistMode(mode);
    if (mode === "employer") {
      setEmployerView("jobs");
    }
  }

  function handleSwitchRole() {
    setAppMode(null);
    persistMode(null);
  }

  function handleJobCreated() {
    setJobsReloadKey((k) => k + 1);
    setEmployerView("jobs");
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

    if (needsRolePicker(me.role) && appMode === null) {
      return <RolePicker onSelect={handleSelectMode} />;
    }

    const mode = appMode ?? (hasEmployerAccess(me.role) && !hasWorkerAccess(me.role) ? "employer" : "worker");

    if (mode === "worker" && hasWorkerAccess(me.role)) {
      return <ProfilePage initData={telegram.initData} />;
    }

    if (mode === "employer" && hasEmployerAccess(me.role)) {
      if (employerView === "create") {
        return (
          <CreateJobPage
            initData={telegram.initData}
            onCreated={handleJobCreated}
            onCancel={() => setEmployerView("jobs")}
          />
        );
      }
      return (
        <EmployerJobsPage
          initData={telegram.initData}
          reloadKey={jobsReloadKey}
          onCreateClick={() => setEmployerView("create")}
        />
      );
    }

    return (
      <section className="card">
        <p className="error">Нет доступа к выбранному режиму.</p>
      </section>
    );
  }

  const showSwitchRole =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    needsRolePicker(meState.me.role) &&
    appMode !== null;

  const showEmployerNav =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    appMode === "employer" &&
    hasEmployerAccess(meState.me.role);

  return (
    <main className="app">
      <div className="app-header">
        <div>
          <h1>OutstaffingBot</h1>
          <p className="subtitle">
            {telegram.inTelegram ? `Telegram: ${telegram.userLabel}` : "Telegram Mini App"}
          </p>
        </div>
        {showSwitchRole ? (
          <button type="button" className="link-btn switch-role-btn" onClick={handleSwitchRole}>
            Сменить роль
          </button>
        ) : null}
      </div>

      {showEmployerNav ? (
        <nav className="app-nav">
          <button
            type="button"
            className={`nav-btn${employerView === "jobs" ? " active" : ""}`}
            onClick={() => setEmployerView("jobs")}
          >
            Заявки
          </button>
          <button
            type="button"
            className={`nav-btn${employerView === "create" ? " active" : ""}`}
            onClick={() => setEmployerView("create")}
          >
            Создать
          </button>
        </nav>
      ) : null}

      {renderContent()}
    </main>
  );
}

export default App;
