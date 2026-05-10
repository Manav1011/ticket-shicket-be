import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  ArrowLeftIcon,
  CheckIcon,
  XIcon,
  DollarSignIcon,
  TicketIcon,
  CalendarIcon,
  MailIcon,
  TagIcon,
} from "lucide-react";
import { b2bService } from "@/services/b2bService";
import { RequestStatusBadge } from "@/components/dashboard/RequestStatusBadge";
import type { B2BRequestDetail } from "@/types/b2b";

export function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [request, setRequest] = useState<B2BRequestDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const [paidDialogOpen, setPaidDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [paidAmount, setPaidAmount] = useState("");
  const [paidNotes, setPaidNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  useEffect(() => {
    const fetchRequest = async () => {
      if (!id) return;
      setIsLoading(true);
      try {
        const data = await b2bService.getRequest(id);
        setRequest(data);
      } catch {
        toast.error("Failed to load request");
        navigate("/dashboard");
      } finally {
        setIsLoading(false);
      }
    };
    fetchRequest();
  }, [id, navigate]);

  const handleApproveFree = async () => {
    if (!request) return;
    setIsActionLoading(true);
    try {
      await b2bService.approveFree(request.id, {});
      toast.success("Request approved (free transfer)");
      navigate("/dashboard");
    } catch {
      toast.error("Failed to approve request");
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleApprovePaid = async () => {
    if (!request || !paidAmount) return;
    setIsActionLoading(true);
    try {
      await b2bService.approvePaid(request.id, {
        amount: parseFloat(paidAmount),
        admin_notes: paidNotes || undefined,
      });
      toast.success("Request approved (paid)");
      navigate("/dashboard");
    } catch {
      toast.error("Failed to approve request");
    } finally {
      setIsActionLoading(false);
      setPaidDialogOpen(false);
    }
  };

  const handleReject = async () => {
    if (!request || !rejectReason.trim()) return;
    setIsActionLoading(true);
    try {
      await b2bService.reject(request.id, { reason: rejectReason.trim() });
      toast.success("Request rejected");
      navigate("/dashboard");
    } catch {
      toast.error("Failed to reject request");
    } finally {
      setIsActionLoading(false);
      setRejectDialogOpen(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
        <Skeleton className="h-8 w-[200px]" />
        <Skeleton className="h-[300px] w-full rounded-xl" />
        <Skeleton className="h-[150px] w-full rounded-xl" />
      </div>
    );
  }

  if (!request) {
    return (
      <div className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
        <p className="text-muted-foreground">Request not found</p>
      </div>
    );
  }

  const isPending = request.status === "pending";
  const formattedDate = request.event_day_date
    ? new Date(request.event_day_date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate("/dashboard")}
        className="w-fit gap-2"
      >
        <ArrowLeftIcon data-icon="inline-start" />
        Back to Dashboard
      </Button>

      {/* Header Card */}
      <Card className="overflow-hidden">
        <div className="h-2 bg-primary" />
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <TicketIcon className="size-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">
                  {request.event_name || "B2B Request"}
                </CardTitle>
                <CardDescription className="font-mono text-xs mt-1">
                  {request.id}
                </CardDescription>
              </div>
            </div>
            <RequestStatusBadge status={request.status} />
          </div>
        </CardHeader>
      </Card>

      {/* Details Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Request Details</CardTitle>
          <CardDescription>
            Information about this ticket request
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
              <TicketIcon className="size-4 mt-0.5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Quantity</p>
                <p className="text-lg font-semibold">{request.quantity} tickets</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
              <CalendarIcon className="size-4 mt-0.5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Event Date</p>
                <p className="text-sm font-medium">{formattedDate || "N/A"}</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
              <TagIcon className="size-4 mt-0.5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Ticket Type</p>
                <p className="text-sm font-medium">
                  {request.ticket_type_name || "N/A"}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
              <MailIcon className="size-4 mt-0.5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Requested By</p>
                <p className="text-sm font-medium">
                  {request.requesting_user_email || "N/A"}
                </p>
              </div>
            </div>
          </div>

          <Separator />

          <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
            <CalendarIcon className="size-4 mt-0.5 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p className="text-sm font-medium">
                {new Date(request.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>

          {request.admin_notes && (
            <>
              <Separator />
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground mb-1">Admin Notes</p>
                <p className="text-sm">{request.admin_notes}</p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Actions Card - Only for pending requests */}
      {isPending && (
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle className="text-lg">Take Action</CardTitle>
            <CardDescription>Approve or reject this request</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row gap-3">
            <Button
              variant="default"
              onClick={handleApproveFree}
              disabled={isActionLoading}
              className="flex-1 gap-2"
            >
              <CheckIcon data-icon="inline-start" />
              Approve Free
            </Button>
            <Button
              variant="outline"
              onClick={() => setPaidDialogOpen(true)}
              disabled={isActionLoading}
              className="flex-1 gap-2"
            >
              <DollarSignIcon data-icon="inline-start" />
              Approve Paid
            </Button>
            <Button
              variant="destructive"
              onClick={() => setRejectDialogOpen(true)}
              disabled={isActionLoading}
              className="flex-1 gap-2"
            >
              <XIcon data-icon="inline-start" />
              Reject
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Approve Paid Dialog */}
      <Dialog open={paidDialogOpen} onOpenChange={setPaidDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Approve as Paid</DialogTitle>
            <DialogDescription>
              Enter the total amount for this ticket purchase. The organizer
              will be notified to complete payment.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="amount">Total Amount</Label>
              <div className="relative">
                <DollarSignIcon className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  value={paidAmount}
                  onChange={(e) => setPaidAmount(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder="Add any notes about this approval..."
                value={paidNotes}
                onChange={(e) => setPaidNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPaidDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleApprovePaid}
              disabled={!paidAmount || isActionLoading}
            >
              {isActionLoading ? "Processing..." : "Approve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Reject Request</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejecting this request. The organizer
              will be notified.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="reason">Reason for Rejection</Label>
              <Textarea
                id="reason"
                placeholder="Enter the reason for rejection..."
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={!rejectReason.trim() || isActionLoading}
            >
              {isActionLoading ? "Rejecting..." : "Reject Request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}