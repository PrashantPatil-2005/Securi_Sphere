import { PageSkeleton } from "@/components/ui/PageSkeleton";

export default function DashboardLoading() {
  return (
    <div className="animate-fade-in">
      <PageSkeleton />
    </div>
  );
}
