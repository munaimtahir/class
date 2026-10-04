import ModulePlaceholder from "../../_components/ModulePlaceholder";

export default function EnrollmentWrongEnrollmentsPage() {
  return (
    <ModulePlaceholder
      title="Wrong Enrollments"
      description="Planned review queue for membership mismatches and incorrect course assignments."
      links={[{ href: "/enrollment/dashboard", label: "Back to Enrollment Dashboard" }]}
    />
  );
}
