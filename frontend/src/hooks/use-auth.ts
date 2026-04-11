/** Auth hook — current user state, login, and logout. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { fetchCurrentUser, logout as logoutApi, requestMagicLink } from "@/api/auth";
import type { UserInfo } from "@/types/schemas";

const AUTH_QUERY_KEY = ["auth", "me"] as const;
const AUTH_STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes

export function useAuth() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: AUTH_QUERY_KEY,
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: AUTH_STALE_TIME_MS,
  });

  const user: UserInfo | null = data?.user ?? null;
  const isAuthenticated = user !== null;

  const loginMutation = useMutation({
    mutationFn: (email: string) => requestMagicLink(email),
  });

  const logoutMutation = useMutation({
    mutationFn: logoutApi,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: AUTH_QUERY_KEY });
      navigate("/login");
    },
  });

  return {
    user,
    isLoading,
    isAuthenticated,
    error,
    login: loginMutation.mutateAsync,
    loginStatus: loginMutation.status,
    loginError: loginMutation.error,
    logout: logoutMutation.mutateAsync,
    logoutStatus: logoutMutation.status,
  };
}
