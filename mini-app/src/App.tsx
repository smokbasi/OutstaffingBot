import { useEffect, useState } from "react";
import "./App.css";

/** Placeholder until @telegram-apps/sdk-react is wired in Phase 1. */
interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: { first_name?: string; username?: string } };
  ready: () => void;
  expand: () => void;
  themeParams: Record<string, string | undefined>;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

function App() {
  const [userLabel, setUserLabel] = useState("гость");
  const [inTelegram, setInTelegram] = useState(false);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;
    if (!webApp) {
      return;
    }
    webApp.ready();
    webApp.expand();
    setInTelegram(true);
    const user = webApp.initDataUnsafe.user;
    if (user?.first_name) {
      setUserLabel(user.username ? `@${user.username}` : user.first_name);
    }
  }, []);

  return (
    <main className="app">
      <h1>OutstaffingBot</h1>
      <p className="subtitle">Telegram Mini App — Phase 0 skeleton</p>
      <section className="card">
        <p>
          {inTelegram
            ? `Открыто в Telegram: ${userLabel}`
            : "Откройте через бота (WebApp) для initData auth в Phase 1."}
        </p>
        <ul>
          <li>👷 Профиль работника — Phase 1</li>
          <li>🏢 Заявки работодателя — Phase 2</li>
          <li>🔍 Поиск вакансий — Phase 3</li>
        </ul>
      </section>
    </main>
  );
}

export default App;
