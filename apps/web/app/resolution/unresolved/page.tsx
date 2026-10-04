import IssueQueuePlaceholder from "../_components/IssueQueuePlaceholder";

export default function ResolutionUnresolvedPage() {
  return (
    <IssueQueuePlaceholder
      title="Unresolved Issues"
      description="Track unresolved operational blockers affecting users in Google Workspace and Classroom flows."
      emptyMessage="No unresolved issues right now."
    />
  );
}
