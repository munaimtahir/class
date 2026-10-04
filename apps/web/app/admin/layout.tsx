// Admin section layout — global sidebar is provided by the root AppShell.
// This layout just passes through children.
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
