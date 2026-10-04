import ModulePlaceholder from "../../_components/ModulePlaceholder";

export default function EnrollmentDashboardPage() {
  return (
    <ModulePlaceholder
      title="Enrollment Dashboard"
      description="Prepared shell for enrollment visibility across course membership workflows."
      links={[
        { href: "/enrollment/course-membership-check", label: "Course Membership Check" },
        { href: "/enrollment/missing-enrollments", label: "Missing Enrollments" },
        { href: "/enrollment/wrong-enrollments", label: "Wrong Enrollments" },
      ]}
    />
  );
}
