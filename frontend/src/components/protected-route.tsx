/** Route guard — redirects to /login if not authenticated. */

import { Navigate, Outlet } from "react-router";
import { useAuth } from "@/hooks/use-auth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading, error } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated || error) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
