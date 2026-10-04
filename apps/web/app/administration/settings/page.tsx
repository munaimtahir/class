import ModulePlaceholder from "../../_components/ModulePlaceholder";

export default function AdministrationSettingsPage() {
  return (
    <ModulePlaceholder
      title="Settings"
      description="Reserved administrative settings area for future platform configuration controls."
      links={[
        { href: "/administration/workspace-connection", label: "Workspace Connection" },
        { href: "/administration/sync-controls", label: "Sync Controls" },
      ]}
    />
  );
}
