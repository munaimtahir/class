import { redirect } from "next/navigation";

export default function LegacyDashboardRoutePage() {
  redirect("/classroom/dashboard");
}
