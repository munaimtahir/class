import Link from "next/link";

export default function ResolutionDashboardPage() {
  const cards = [
    { label: "Unresolved", value: "0", href: "/resolution/unresolved" },
    { label: "Assigned to Me", value: "0", href: "/resolution/assigned" },
    { label: "Escalated", value: "0", href: "/resolution/escalated" },
    { label: "New This Week", value: "0", href: "/resolution/issues" },
  ];

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Issues Dashboard</h1>
        <p className="text-slate-600 mt-2">
          Operational issue tracking for Google Workspace and Classroom workflow access problems.
        </p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {cards.map((card) => (
          <Link key={card.label} href={card.href} className="rounded-xl bg-white p-4 shadow border border-slate-200 hover:bg-slate-50">
            <p className="text-xs text-slate-500">{card.label}</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{card.value}</p>
          </Link>
        ))}
      </section>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h2 className="font-semibold text-lg text-slate-900">Scope Guardrail</h2>
        <p className="text-sm text-slate-600 mt-2">
          This center is limited to account readiness, classroom/course access, session mapping, Meet generation,
          and publish workflow resolution. General IT helpdesk issues remain out of scope.
        </p>
      </section>
    </div>
  );
}
