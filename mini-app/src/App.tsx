import { useEffect, useState, type FormEvent } from "react";
import "./App.css";
import { getMe, upsertEmployerProfile, type MeResponse } from "./api/client";
import { CreateJobPage } from "./pages/CreateJobPage";
import { EmployerApplicationsPage } from "./pages/EmployerApplicationsPage";
import { EmployerJobsPage } from "./pages/EmployerJobsPage";
import { MyApplicationsPage } from "./pages/MyApplicationsPage";
import { NotificationsSettingsPage } from "./pages/NotificationsSettingsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { VacancyDetailPage } from "./pages/VacancyDetailPage";
import { VacancyListPage } from "./pages/VacancyListPage";
import { applyTelegramTheme, triggerHaptic } from "./lib/telegram";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        initDataUnsafe: { user?: { first_name?: string; username?: string } };
        themeParams?: Record<string, string>;
        ready: () => void;
        expand: () => void;
        setHeaderColor?: (color: string) => void;
        setBackgroundColor?: (color: string) => void;
        HapticFeedback?: {
          impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
          notificationOccurred?: (type: "error" | "success" | "warning") => void;
        };
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
type EmployerView = "jobs" | "create" | "applications";
type WorkerView = "profile" | "vacancies" | "vacancy-detail" | "applications" | "notifications";

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

const VACANCY_DEEP_LINK_RE = /^\/vacancy\/([0-9a-f-]{36})$/i;
const EMPLOYER_JOB_DEEP_LINK_RE = /^\/employer\/job\/([0-9a-f-]{36})$/i;

function parseVacancyDeepLink(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const match = window.location.pathname.match(VACANCY_DEEP_LINK_RE);
  return match?.[1] ?? null;
}

function parseEmployerJobDeepLink(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const match = window.location.pathname.match(EMPLOYER_JOB_DEEP_LINK_RE);
  return match?.[1] ?? null;
}

function readInitialRoute(): {
  appMode: AppMode | null;
  workerView: WorkerView;
  employerView: EmployerView;
  vacancyId: string | null;
  employerJobId: string | null;
} {
  const vacancyId = parseVacancyDeepLink();
  if (vacancyId) {
    return {
      appMode: "worker",
      workerView: "vacancy-detail",
      employerView: "jobs",
      vacancyId,
      employerJobId: null,
    };
  }
  const employerJobId = parseEmployerJobDeepLink();
  if (employerJobId) {
    return {
      appMode: "employer",
      workerView: "vacancies",
      employerView: "applications",
      vacancyId: null,
      employerJobId,
    };
  }
  return {
    appMode: null,
    workerView: "vacancies",
    employerView: "jobs",
    vacancyId: null,
    employerJobId: null,
  };
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
        <button type="button" className="role-card" onClick={() => {
          triggerHaptic("light");
          onSelect("worker");
        }}>
          <span className="role-card-icon">👷</span>
          <span className="role-card-title">Я ищу работу</span>
          <span className="role-card-desc">Профиль, опыт и настройки для поиска смен</span>
        </button>
        <button type="button" className="role-card" onClick={() => {
          triggerHaptic("light");
          onSelect("employer");
        }}>
          <span className="role-card-icon">🏢</span>
          <span className="role-card-title">Я работодатель</span>
          <span className="role-card-desc">Заявки на персонал и создание новых смен</span>
        </button>
      </div>
    </section>
  );
}

function EmployerSetupPrompt({
  initData,
  onRegistered,
}: {
  initData: string;
  onRegistered: () => void;
}) {
  const [companyName, setCompanyName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = companyName.trim();
    if (!trimmed) {
      setError("Укажите название компании");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await upsertEmployerProfile(initData, { company_name: trimmed });
      onRegistered();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось сохранить профиль";
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Профиль работодателя</h2>
      <p className="hint">
        Зарегистрируйтесь как работодатель в боте (🏢) или укажите название компании ниже.
      </p>
      <form className="profile-form" onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Название компании</span>
          <input
            type="text"
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            placeholder="ООО «Пример»"
            disabled={busy}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <div className="form-actions">
          <button type="submit" className="btn" disabled={busy}>
            {busy ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </form>
    </section>
  );
}

function App() {
  const [telegram] = useState(readTelegramContext);
  const [initialRoute] = useState(readInitialRoute);
  const [meState, setMeState] = useState<MeState>({ status: "loading" });
  const [appMode, setAppMode] = useState<AppMode | null>(initialRoute.appMode);
  const [employerView, setEmployerView] = useState<EmployerView>(initialRoute.employerView);
  const [workerView, setWorkerView] = useState<WorkerView>(initialRoute.workerView);
  const [selectedVacancyId, setSelectedVacancyId] = useState<string | null>(initialRoute.vacancyId);
  const [selectedEmployerJobId, setSelectedEmployerJobId] = useState<string | null>(
    initialRoute.employerJobId,
  );
  const [selectedEmployerJobTitle, setSelectedEmployerJobTitle] = useState<string | null>(null);
  const [jobsReloadKey, setJobsReloadKey] = useState(0);

  useEffect(() => {
    applyTelegramTheme();
  }, []);

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
    if (mode === "employer") {
      setEmployerView("jobs");
      setSelectedEmployerJobId(null);
    }
    if (mode === "worker") {
      setWorkerView("vacancies");
      setSelectedVacancyId(null);
    }
  }

  function handleViewEmployerApplications(jobId: string, jobTitle: string) {
    setSelectedEmployerJobId(jobId);
    setSelectedEmployerJobTitle(jobTitle);
    setEmployerView("applications");
  }

  function handleSwitchRole() {
    setAppMode(null);
  }

  function handleEmployerRegistered() {
    setMeState((prev) => {
      if (prev.status !== "ready") {
        return prev;
      }
      return {
        status: "ready",
        me: { ...prev.me, has_employer_profile: true },
      };
    });
    setJobsReloadKey((key) => key + 1);
  }

  function handleJobCreated() {
    setJobsReloadKey((key) => key + 1);
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

    if (appMode === null) {
      return <RolePicker onSelect={handleSelectMode} />;
    }

    if (appMode === "worker") {
      if (workerView === "applications") {
        return <MyApplicationsPage initData={telegram.initData} />;
      }
      if (workerView === "profile") {
        return <ProfilePage initData={telegram.initData} />;
      }
      if (workerView === "notifications") {
        return <NotificationsSettingsPage initData={telegram.initData} />;
      }
      if (workerView === "vacancy-detail" && selectedVacancyId) {
        return (
          <VacancyDetailPage
            initData={telegram.initData}
            vacancyId={selectedVacancyId}
            onBack={() => setWorkerView("vacancies")}
          />
        );
      }
      return (
        <VacancyListPage
          initData={telegram.initData}
          onOpenVacancy={(id) => {
            setSelectedVacancyId(id);
            setWorkerView("vacancy-detail");
          }}
        />
      );
    }

    if (!me.has_employer_profile) {
      return (
        <EmployerSetupPrompt
          initData={telegram.initData}
          onRegistered={handleEmployerRegistered}
        />
      );
    }

    if (employerView === "create") {
      return (
        <CreateJobPage
          initData={telegram.initData}
          onCreated={handleJobCreated}
          onCancel={() => setEmployerView("jobs")}
        />
      );
    }

    if (employerView === "applications" && selectedEmployerJobId) {
      return (
        <EmployerApplicationsPage
          initData={telegram.initData}
          jobId={selectedEmployerJobId}
          jobTitle={selectedEmployerJobTitle ?? undefined}
          onBack={() => {
            setEmployerView("jobs");
            setSelectedEmployerJobId(null);
          }}
        />
      );
    }

    return (
      <EmployerJobsPage
        initData={telegram.initData}
        reloadKey={jobsReloadKey}
        onCreateClick={() => setEmployerView("create")}
        onViewApplications={handleViewEmployerApplications}
      />
    );
  }

  const showSwitchRole =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    appMode !== null;

  const showEmployerNav =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    appMode === "employer" &&
    meState.me.has_employer_profile;

  const showWorkerNav =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    appMode === "worker";

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

      {showWorkerNav ? (
        <nav className="app-nav">
          <button
            type="button"
            className={`nav-btn${workerView === "vacancies" || workerView === "vacancy-detail" ? " active" : ""}`}
            onClick={() => {
              setWorkerView("vacancies");
              setSelectedVacancyId(null);
            }}
          >
            Поиск
          </button>
          <button
            type="button"
            className={`nav-btn${workerView === "applications" ? " active" : ""}`}
            onClick={() => setWorkerView("applications")}
          >
            Мои отклики
          </button>
          <button
            type="button"
            className={`nav-btn${workerView === "profile" ? " active" : ""}`}
            onClick={() => setWorkerView("profile")}
          >
            Профиль
          </button>
          <button
            type="button"
            className={`nav-btn${workerView === "notifications" ? " active" : ""}`}
            onClick={() => setWorkerView("notifications")}
          >
            Уведомления
          </button>
        </nav>
      ) : null}

      {showEmployerNav ? (
        <nav className="app-nav">
          <button
            type="button"
            className={`nav-btn${employerView === "jobs" || employerView === "applications" ? " active" : ""}`}
            onClick={() => {
              setEmployerView("jobs");
              setSelectedEmployerJobId(null);
            }}
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
