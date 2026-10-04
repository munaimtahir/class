import IssueQueuePlaceholder from "../_components/IssueQueuePlaceholder";

export default function ResolutionAllIssuesPage() {
  return (
    <IssueQueuePlaceholder
      title="All Issues"
      description="Unified queue for application-related user access and workflow issues."
      emptyMessage="No issues are recorded yet. Create an issue when a user cannot access the expected Workspace/Classroom flow."
    />
  );
}
