import { Badge } from "@/components/ui/badge";
import type { B2BRequestStatus } from "@/types/b2b";

interface RequestStatusBadgeProps {
  status: B2BRequestStatus;
}

const statusConfig: Record<B2BRequestStatus, { label: string; variant: "secondary" | "default" | "destructive" }> = {
  pending: { label: "Pending", variant: "secondary" },
  approved_free: { label: "Approved (Free)", variant: "default" },
  approved_paid: { label: "Approved (Paid)", variant: "default" },
  rejected: { label: "Rejected", variant: "destructive" },
  expired: { label: "Expired", variant: "secondary" },
};

export function RequestStatusBadge({ status }: RequestStatusBadgeProps) {
  const config = statusConfig[status] ?? { label: status, variant: "secondary" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}