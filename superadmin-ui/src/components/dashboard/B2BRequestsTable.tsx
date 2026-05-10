import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Empty, EmptyHeader, EmptyMedia, EmptyTitle, EmptyDescription } from "@/components/ui/empty";
import { ChevronLeftIcon, ChevronRightIcon, EyeIcon } from "lucide-react";
import { b2bService } from "@/services/b2bService";
import { RequestStatusBadge } from "./RequestStatusBadge";
import type { B2BRequestListResponse, B2BRequestStatus } from "@/types/b2b";

interface B2BRequestsTableProps {
  statusFilter: string;
  searchQuery: string;
}

const PAGE_SIZE = 20;

export function B2BRequestsTable({ statusFilter, searchQuery }: B2BRequestsTableProps) {
  const navigate = useNavigate();
  const [requests, setRequests] = useState<B2BRequestListResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [statusFilter, searchQuery]);

  useEffect(() => {
    const fetchRequests = async () => {
      setIsLoading(true);
      try {
        const status = statusFilter === "all" ? undefined : (statusFilter as B2BRequestStatus);
        const data = await b2bService.listRequests({ status, limit: PAGE_SIZE, offset });
        setRequests(data);
      } catch {
        setRequests([]);
      } finally {
        setIsLoading(false);
      }
    };
    fetchRequests();
  }, [statusFilter, offset]);

  const filteredRequests = searchQuery
    ? requests.filter((r) =>
        r.id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : requests;

  const handlePrev = () => setOffset((prev) => Math.max(0, prev - PAGE_SIZE));
  const handleNext = () => setOffset((prev) => prev + PAGE_SIZE);

  if (isLoading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Request ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-[100px]">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                <TableCell><Skeleton className="h-4 w-[200px]" /></TableCell>
                <TableCell><Skeleton className="h-5 w-[100px]" /></TableCell>
                <TableCell><Skeleton className="h-4 w-[60px]" /></TableCell>
                <TableCell><Skeleton className="h-4 w-[120px]" /></TableCell>
                <TableCell><Skeleton className="h-8 w-[80px]" /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (filteredRequests.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon"><EyeIcon /></EmptyMedia>
          <EmptyTitle>No requests found</EmptyTitle>
          <EmptyDescription>
            {searchQuery ? "Try adjusting your search." : "No B2B requests yet."}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Request ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Quantity</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="w-[100px]">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredRequests.map((request) => (
              <TableRow
                key={request.id}
                className="cursor-pointer"
                onClick={() => navigate(`/dashboard/requests/${request.id}`)}
              >
                <TableCell className="font-mono text-sm truncate max-w-[300px]">
                  {request.id}
                </TableCell>
                <TableCell>
                  <RequestStatusBadge status={request.status} />
                </TableCell>
                <TableCell>{request.quantity}</TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(request.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/dashboard/requests/${request.id}`);
                    }}
                  >
                    <EyeIcon data-icon="inline-end" />
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-end gap-2 mt-4">
        <span className="text-sm text-muted-foreground">
          Showing {offset + 1}-{Math.min(offset + filteredRequests.length, offset + PAGE_SIZE)}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={offset === 0}
        >
          <ChevronLeftIcon data-icon="inline-start" />
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNext}
          disabled={filteredRequests.length < PAGE_SIZE}
        >
          Next
          <ChevronRightIcon data-icon="inline-end" />
        </Button>
      </div>
    </>
  );
}