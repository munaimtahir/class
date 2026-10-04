"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../lib/api";

type DirectoryIssue = {
  id: number;
  directory_user_email: string | null;
  issue_type: string;
  status: string;
  severity: string;
};

export default function DirectoryOuIssuesPage() {
  const [issues, setIssues] = useState<DirectoryIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listDirectoryIssues({}).then((data) => setIssues(data || [])).finally(() => setLoading(false));
  }, []);

  const ouIssues = useMemo(
    () =>
      issues.filter((issue) => {
        const type = issue.issue_type.toLowerCase();
        return type.includes("org") || type.includes("ou");
      }),
    [issues],
  );

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Organizational Unit Issues</h1>
        <p className="text-slate-600 mt-2">Review OU-related mismatches that affect course access or policy routing.</p>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading OU issues…</p>
        ) : ouIssues.length === 0 ? (
          <p className="text-slate-600">No OU issues detected.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2">Issue #</th>
                <th className="text-left p-2">User</th>
                <th className="text-left p-2">Type</th>
                <th className="text-left p-2">Severity</th>
                <th className="text-left p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {ouIssues.map((issue) => (
                <tr key={issue.id} className="border-b">
                  <td className="p-2">#{issue.id}</td>
                  <td className="p-2">{issue.directory_user_email || "Unknown"}</td>
                  <td className="p-2">{issue.issue_type}</td>
                  <td className="p-2 capitalize">{issue.severity}</td>
                  <td className="p-2 capitalize">{issue.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
