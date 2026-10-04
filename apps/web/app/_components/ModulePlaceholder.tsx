import Link from "next/link";

type Props = {
  title: string;
  description: string;
  statusLabel?: string;
  links?: Array<{ href: string; label: string }>;
};

export default function ModulePlaceholder({
  title,
  description,
  statusLabel = "Planned UI Shell",
  links = [],
}: Props) {
  return (
    <div className="max-w-5xl">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <p className="text-slate-600 mt-2">{description}</p>
        <p className="text-xs font-semibold text-sky-700 mt-3 uppercase tracking-wide">
          {statusLabel}
        </p>
      </header>

      {links.length > 0 ? (
        <section className="rounded-xl bg-white p-5 shadow border border-slate-200 mt-4">
          <h2 className="text-lg font-semibold text-slate-900">Quick Links</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
