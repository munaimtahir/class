import { redirect } from "next/navigation";

export default function LegacyAdminIndexPage() {
  redirect("/administration/workspace-connection");
}
