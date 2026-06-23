export type TelegramContact = {
  label: string;
  href: string;
};

export function buildTelegramContact(
  username: string | null | undefined,
  telegramId: number | null | undefined,
): TelegramContact | null {
  if (username) {
    const handle = username.replace(/^@/, "");
    return { label: `@${handle}`, href: `https://t.me/${handle}` };
  }
  if (telegramId != null) {
    return { label: "Telegram", href: `tg://user?id=${telegramId}` };
  }
  return null;
}

type ContactBlockProps = {
  title: string;
  phone: string | null | undefined;
  telegramUsername: string | null | undefined;
  telegramId: number | null | undefined;
  companyName?: string | null;
};

export function ContactBlock({
  title,
  phone,
  telegramUsername,
  telegramId,
  companyName,
}: ContactBlockProps) {
  const telegram = buildTelegramContact(telegramUsername, telegramId);
  if (!phone && !telegram && !companyName) {
    return null;
  }

  return (
    <div className="contact-block">
      <strong>{title}</strong>
      {companyName ? <p>{companyName}</p> : null}
      {phone ? (
        <p>
          <a href={`tel:${phone}`}>{phone}</a>
        </p>
      ) : null}
      {telegram ? (
        <p>
          <a href={telegram.href} target="_blank" rel="noopener noreferrer">
            {telegram.label}
          </a>
        </p>
      ) : null}
    </div>
  );
}
