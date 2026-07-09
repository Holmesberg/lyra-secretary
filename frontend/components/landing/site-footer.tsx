const FOOTER_LINKS = [
  { label: "Privacy", href: "/privacy" },
  { label: "Terms", href: "/terms" },
];

export function SiteFooter() {
  return (
    <footer className="relative border-t border-hairline py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 md:flex-row md:px-8">
        <p className="text-xs text-dust-deep">
          © 2026 Barzakh · Behavioral measurement with a productivity interface
        </p>
        <div className="flex items-center gap-5">
          {FOOTER_LINKS.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="text-xs text-dust transition-colors hover:text-parchment"
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
