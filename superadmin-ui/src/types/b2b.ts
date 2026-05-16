export type B2BRequestStatus =
  | "pending"
  | "approved_free"
  | "approved_paid"
  | "rejected"
  | "expired";

export interface B2BRequest {
  id: string;
  requesting_user_id: string;
  event_id: string;
  event_day_id: string;
  ticket_type_id: string;
  quantity: number;
  status: B2BRequestStatus;
  reviewed_by_admin_id: string | null;
  admin_notes: string | null;
  allocation_id: string | null;
  order_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface B2BRequestDetail {
  id: string;
  quantity: number;
  status: B2BRequestStatus;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
  event_name: string | null;
  event_day_date: string | null;
  ticket_type_name: string | null;
  requesting_user_email: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface B2BRequestListResponse {
  id: string;
  status: B2BRequestStatus;
  quantity: number;
  created_at: string;
  event_id: string;
  event_day_id: string;
  requesting_user_id: string;
}

export interface ApproveFreeRequest {
  admin_notes?: string;
}

export interface ApprovePaidRequest {
  amount: number;
  admin_notes?: string;
}

export interface RejectRequest {
  reason: string;
}
