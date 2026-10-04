import ModulePlaceholder from "../../_components/ModulePlaceholder";

export default function EnrollmentMissingEnrollmentsPage() {
  return (
    <ModulePlaceholder
      title="Missing Enrollments"
      description="Planned queue for users who should be enrolled but are not present in target courses."
      links={[{ href: "/enrollment/dashboard", label: "Back to Enrollment Dashboard" }]}
    />
  );
}
