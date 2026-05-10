import apiClient from "./apiClient";
import type {
  B2BRequest,
  B2BRequestDetail,
  B2BRequestListResponse,
  B2BRequestStatus,
  ApproveFreeRequest,
  ApprovePaidRequest,
  RejectRequest,
  ApiResponse,
} from "@/types/b2b";

interface ListB2BRequestsParams {
  status?: B2BRequestStatus;
  limit?: number;
  offset?: number;
}

export const b2bService = {
  async listRequests(params: ListB2BRequestsParams = {}) {
    const { status, limit = 50, offset = 0 } = params;
    const response = await apiClient.get<ApiResponse<B2BRequestListResponse[]>>(
      "/api/superadmin/b2b/requests",
      {
        params: { status, limit, offset },
      }
    );
    return response.data.data;
  },

  async listPendingRequests(params: { limit?: number; offset?: number } = {}) {
    const { limit = 50, offset = 0 } = params;
    const response = await apiClient.get<ApiResponse<B2BRequestListResponse[]>>(
      "/api/superadmin/b2b/requests/pending",
      { params: { limit, offset } }
    );
    return response.data.data;
  },

  async getRequest(requestId: string): Promise<B2BRequestDetail> {
    const response = await apiClient.get<ApiResponse<B2BRequestDetail>>(
      `/api/superadmin/b2b/requests/${requestId}`
    );
    return response.data.data;
  },

  async approveFree(requestId: string, data: ApproveFreeRequest) {
    const response = await apiClient.post<ApiResponse<B2BRequest>>(
      `/api/superadmin/b2b/requests/${requestId}/approve-free`,
      data
    );
    return response.data.data;
  },

  async approvePaid(requestId: string, data: ApprovePaidRequest) {
    const response = await apiClient.post<ApiResponse<B2BRequest>>(
      `/api/superadmin/b2b/requests/${requestId}/approve-paid`,
      data
    );
    return response.data.data;
  },

  async reject(requestId: string, data: RejectRequest) {
    const response = await apiClient.post<ApiResponse<B2BRequest>>(
      `/api/superadmin/b2b/requests/${requestId}/reject`,
      data
    );
    return response.data.data;
  },
};
