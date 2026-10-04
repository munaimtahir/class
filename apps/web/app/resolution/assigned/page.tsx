import IssueQueuePlaceholder from "../_components/IssueQueuePlaceholder";

export default function ResolutionAssignedPage() {
  return (
    <IssueQueuePlaceholder
      title="Assigned to Me"
      description="Personal queue for issues currently assigned to the logged-in operator."
      emptyMessage="No issues are currently assigned to you."
    />
  );
}
