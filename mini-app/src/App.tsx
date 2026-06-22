import { lazy, Suspense, useEffect, useState, type FormEvent } from "react";
import "./App.css";
import { getMe, upsertEmployerProfile, type MeResponse } from "./api/client";

const CreateJobPage = lazy(() =>
  import("./pages/CreateJobPage").then((m) => ({ default: m.CreateJobPage })),
);
const EmployerJobsPage = lazy(() =>
  import("./pages/EmployerJobsPage").then((m) => ({ default: m.EmployerJobsPage })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((m) => ({ default: m.ProfilePage })),
);
const VacancyDetailPage = lazy(() =>
  import("./pages/VacancyDetailPage").then((m) => ({ default: m.VacancyDetailPage })),
);
const VacancyListPage = lazy(() =>
  import("./pages/VacancyListPage").then((m) => ({ default: m.VacancyListPage })),
);
const MyApplicationsPage = lazy(() =>
  import("./pages/MyApplicationsPage").then((m) => ({ default: m.MyApplicationsPage })),
);
const NotificationsSettingsPage = lazy(() =>
  import("./pages/NotificationsSettingsPage").then((m) => ({ default: m.NotificationsSettingsPage })),
);

function PageFallback() {
  return <p className="status">Загрузка…</p>;
}


declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string;
        initDataUnsafe: { user?: { first_name?: string; username?: string }; start_param?: string };
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
type WorkerView = "profile" | "vacancies" | "vacancy-detail" | "applications" | "notifications";

type MeState =
  | { status: "idle" }
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
const STARTAPP_VACANCY_RE = /^vacancy_([0-9a-f-]{36})$/i;

function parseVacancyDeepLink(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const match = window.location.pathname.match(VACANCY_DEEP_LINK_RE);
  return match?.[1] ?? null;
}

function parseVacancyStartParam(): string | null {
  const startParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
  if (!startParam) {
    return null;
  }
  const match = startParam.match(STARTAPP_VACANCY_RE);
  return match?.[1] ?? null;
}

function readInitialWorkerRoute(): {
  appMode: AppMode | null;
  workerView: WorkerView;
  vacancyId: string | null;
} {
  const vacancyId = parseVacancyDeepLink() ?? parseVacancyStartParam();
  if (vacancyId) {
    return { appMode: "worker", workerView: "vacancy-detail", vacancyId };
  }
  return { appMode: null, workerView: "vacancies", vacancyId: null };
}

function useTelegramContext(): TelegramContext {
  const [telegram, setTelegram] = useState(readTelegramContext);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    if (!webApp) {
      return;
    }

    function syncContext() {
      setTelegram(readTelegramContext());
    }

    syncContext();
    // Some Telegram clients populate initData shortly after WebApp.ready().
    const retryTimers = [50, 150].map((delay) =>
      window.setTimeout(syncContext, delay),
    );

    return () => {
      retryTimers.forEach((timerId) => window.clearTimeout(timerId));
    };
  }, []);

  return telegram;
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
  const telegram = useTelegramContext();
  const [initialRoute] = useState(readInitialWorkerRoute);
  const [meState, setMeState] = useState<MeState>({ status: "idle" });
  const [appMode, setAppMode] = useState<AppMode | null>(initialRoute.appMode);
  const [employerView, setEmployerView] = useState<EmployerView>("jobs");
  const [workerView, setWorkerView] = useState<WorkerView>(initialRoute.workerView);
  const [selectedVacancyId, setSelectedVacancyId] = useState<string | null>(initialRoute.vacancyId);
  const [jobsReloadKey, setJobsReloadKey] = useState(0);
  const [vacanciesReloadKey, setVacanciesReloadKey] = useState(0);

  useEffect(() => {
    if (!telegram.inTelegram || !telegram.initData) {
      setMeState({ status: "idle" });
      return;
    }

    let cancelled = false;
    setMeState({ status: "loading" });
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
    }
    if (mode === "worker") {
      setWorkerView("vacancies");
      setSelectedVacancyId(null);
    }
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

    if (appMode === null) {
      return <RolePicker onSelect={handleSelectMode} />;
    }

    if (appMode === "worker") {
      return (
        <Suspense fallback={<PageFallback />}>
          {workerView === "applications" ? (
            <MyApplicationsPage initData={telegram.initData} />
          ) : workerView === "notifications" ? (
            <NotificationsSettingsPage initData={telegram.initData} />
          ) : workerView === "profile" ? (
            <ProfilePage initData={telegram.initData} />
          ) : workerView === "vacancy-detail" && selectedVacancyId ? (
            <VacancyDetailPage
              initData={telegram.initData}
              vacancyId={selectedVacancyId}
              onBack={() => setWorkerView("vacancies")}
            />
          ) : (
            <VacancyListPage
              initData={telegram.initData}
              reloadKey={vacanciesReloadKey}
              onOpenVacancy={(id) => {
                setSelectedVacancyId(id);
                setWorkerView("vacancy-detail");
              }}
            />
          )}
        </Suspense>
      );
    }

    if (meState.status === "idle" || meState.status === "loading") {
      return <p className="status">Загрузка профиля…</p>;
    }

    if (meState.status === "error") {
      return (
        <section className="card">
          <p className="error">{meState.message}</p>
        </section>
      );
    }

    const { me } = meState;


    if (!me.has_employer_profile) {
      return (
        <EmployerSetupPrompt
          initData={telegram.initData}
          onRegistered={handleEmployerRegistered}
        />
      );
    }

    return (
      <Suspense fallback={<PageFallback />}>
        {employerView === "create" ? (
          <CreateJobPage
            initData={telegram.initData}
            onCreated={handleJobCreated}
            onCancel={() => setEmployerView("jobs")}
          />
        ) : (
          <EmployerJobsPage
            initData={telegram.initData}
            reloadKey={jobsReloadKey}
            onCreateClick={() => setEmployerView("create")}
          />
        )}
      </Suspense>
    );
  }

  const showSwitchRole = telegram.inTelegram && telegram.initData && appMode !== null;

  const showEmployerNav =
    telegram.inTelegram &&
    telegram.initData &&
    meState.status === "ready" &&
    appMode === "employer" &&
    meState.me.has_employer_profile;

  const showWorkerNav = telegram.inTelegram && telegram.initData && appMode === "worker";

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
              setVacanciesReloadKey((key) => key + 1);
            }}
          >
            Поиск
          </button>
          <button
            type="button"
            className={`nav-btn${workerView === "applications" ? " active" : ""}`}
            onClick={() => setWorkerView("applications")}
          >
            Отклики
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
