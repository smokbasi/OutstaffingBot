import { useState } from "react";
import "./App.css";
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

function App() {
  const [telegram] = useState(readTelegramContext);

  return (
    <main className="app">
      <h1>OutstaffingBot</h1>
      <p className="subtitle">
        {telegram.inTelegram ? `Telegram: ${telegram.userLabel}` : "Telegram Mini App"}
      </p>

      {telegram.inTelegram && telegram.initData ? (
        <ProfilePage initData={telegram.initData} />
      ) : (
        <section className="card">
          <p>
            {telegram.inTelegram
              ? "Нет initData — откройте приложение через синюю кнопку бота."
              : "Откройте через бота (WebApp) для просмотра профиля."}
          </p>
        </section>
      )}
    </main>
  );
}

export default App;
