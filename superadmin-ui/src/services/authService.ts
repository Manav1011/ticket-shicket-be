import apiClient from "./apiClient";
import type { LoginRequest, LoginResponse } from "@/types/auth";

export const authService = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<{ data: LoginResponse }>(
      "/api/user/sign-in",
      credentials
    );
    return response.data.data;
  },

  logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  getToken() {
    return localStorage.getItem("access_token");
  },

  isAuthenticated() {
    return !!localStorage.getItem("access_token");
  },
};
