const THEME_VAR_MAP: Record<string, string> = {
  bg_color: "--tg-theme-bg-color",
  text_color: "--tg-theme-text-color",
  hint_color: "--tg-theme-hint-color",
  link_color: "--tg-theme-link-color",
  button_color: "--tg-theme-button-color",
  button_text_color: "--tg-theme-button-text-color",
  secondary_bg_color: "--tg-theme-secondary-bg-color",
  header_bg_color: "--tg-theme-header-bg-color",
  accent_text_color: "--tg-theme-accent-text-color",
  section_bg_color: "--tg-theme-section-bg-color",
  section_header_text_color: "--tg-theme-section-header-text-color",
  subtitle_text_color: "--tg-theme-subtitle-text-color",
  destructive_text_color: "--tg-theme-destructive-text-color",
};

export function applyTelegramTheme(): void {
  const webApp = window.Telegram?.WebApp;
  if (!webApp) {
    return;
  }

  const params = webApp.themeParams ?? {};
  const root = document.documentElement;

  for (const [key, cssVar] of Object.entries(THEME_VAR_MAP)) {
    const value = params[key as keyof typeof params];
    if (value) {
      root.style.setProperty(cssVar, value);
    }
  }

  if (typeof webApp.setHeaderColor === "function" && params.bg_color) {
    webApp.setHeaderColor(params.bg_color);
  }
  if (typeof webApp.setBackgroundColor === "function" && params.bg_color) {
    webApp.setBackgroundColor(params.bg_color);
  }
}

export function triggerHaptic(type: "light" | "medium" | "heavy" = "medium"): void {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(type);
}

export function triggerNotificationHaptic(type: "error" | "success" | "warning" = "success"): void {
  window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.(type);
}
