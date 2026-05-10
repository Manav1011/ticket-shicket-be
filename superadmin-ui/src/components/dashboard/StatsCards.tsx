import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  TicketIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  type LucideIcon,
} from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
}

function StatCard({ title, value, description, icon: Icon }: StatCardProps) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
      <CardHeader className="flex flex-row items-center justify-between pb-2 relative">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <div className="p-2 rounded-lg bg-primary/10">
          <Icon className="size-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent className="relative">
        <div className="text-3xl font-bold text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </CardContent>
    </Card>
  );
}

interface StatsCardsProps {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export function StatsCards({ total, pending, approved, rejected }: StatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Requests"
        value={total}
        description="All B2B requests"
        icon={TicketIcon}
      />
      <StatCard
        title="Pending"
        value={pending}
        description="Awaiting review"
        icon={ClockIcon}
      />
      <StatCard
        title="Approved"
        value={approved}
        description="Fulfilled requests"
        icon={CheckCircleIcon}
      />
      <StatCard
        title="Rejected"
        value={rejected}
        description="Declined requests"
        icon={XCircleIcon}
      />
    </div>
  );
}