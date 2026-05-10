import { useState, useEffect } from "react";
import { StatsCards } from "@/components/dashboard/StatsCards";
import { FiltersBar } from "@/components/dashboard/FiltersBar";
import { B2BRequestsTable } from "@/components/dashboard/B2BRequestsTable";
import { b2bService } from "@/services/b2bService";

export function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, rejected: 0 });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const allData = await b2bService.listRequests({ limit: 100 });
        const pendingData = await b2bService.listPendingRequests({ limit: 100 });

        const total = allData.length;
        const pending = pendingData.length;
        const approved = allData.filter(
          (r) => r.status === "approved_free" || r.status === "approved_paid"
        ).length;
        const rejected = allData.filter((r) => r.status === "rejected").length;

        setStats({ total, pending, approved, rejected });
      } catch {
        // Keep zeros on error
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">B2B Requests</h1>
        <p className="text-muted-foreground">
          Manage and review bulk ticket requests from organizers
        </p>
      </div>

      <StatsCards
        total={stats.total}
        pending={stats.pending}
        approved={stats.approved}
        rejected={stats.rejected}
      />

      <FiltersBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
      />

      <B2BRequestsTable statusFilter={statusFilter} searchQuery={searchQuery} />
    </div>
  );
}