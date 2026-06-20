import { useEffect, useState } from "react";
import "./App.css";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initDataUnsafe: { user?: { first_name?: string; username?: string } };
      };
    };
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
    setInTelegram(true);
    const user = webApp.initDataUnsafe?.user;
    if (user?.first_name) {
      setUserLabel(user.username ? `@${user.username}` : user.first_name);
    }
  }, []);

  return (
    <main className="app">
      <h1>OutstaffingBot</h1>
      <p className="subtitle">Telegram Mini App</p>
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
