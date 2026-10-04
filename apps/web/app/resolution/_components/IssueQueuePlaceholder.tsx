import Link from "next/link";

type Props = {
  title: string;
  description: string;
  emptyMessage: string;
};

export default function IssueQueuePlaceholder({ title, description, emptyMessage }: Props) {
  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        <p className="text-slate-600 mt-2">{description}</p>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900">Operational Queue</h2>
        <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600">
          {emptyMessage}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/resolution/new" className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">
            Create New Issue
          </Link>
          <Link href="/resolution/issues" className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50">
            View All Issues
          </Link>
        </div>
      </section>
    </div>
  );
}
