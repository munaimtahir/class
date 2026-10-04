import IssueQueuePlaceholder from "../_components/IssueQueuePlaceholder";

export default function ResolutionEscalatedPage() {
  return (
    <IssueQueuePlaceholder
      title="Escalated Issues"
      description="High-priority cases requiring escalation or cross-team intervention."
      emptyMessage="No escalated issues are currently open."
    />
  );
}
