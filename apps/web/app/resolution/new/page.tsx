import ModulePlaceholder from "../../_components/ModulePlaceholder";

export default function ResolutionNewIssuePage() {
  return (
    <ModulePlaceholder
      title="New Issue"
      description="Structured issue intake form for workflow-related access problems is prepared here."
      statusLabel="UI scaffold ready"
      links={[
        { href: "/resolution/issues", label: "Back to All Issues" },
        { href: "/resolution/dashboard", label: "Open Issues Dashboard" },
      ]}
    />
  );
}
