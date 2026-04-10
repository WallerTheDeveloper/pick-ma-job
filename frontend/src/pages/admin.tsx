/** Admin users page — lists all users with stats. Admin-only. */

import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { fetchAdminUsers } from "@/api/admin";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { UserStats } from "@/types/schemas";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AdminPage() {
  const { user, isLoading: authLoading } = useAuth();

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: fetchAdminUsers,
    enabled: user?.is_admin === true,
  });

  if (authLoading) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  if (isLoading) {
    return <p className="text-muted-foreground">Loading users...</p>;
  }

  if (error) {
    return (
      <p className="text-destructive">
        Failed to load users: {error instanceof Error ? error.message : "Unknown error"}
      </p>
    );
  }

  const users: readonly UserStats[] = data?.users ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Admin — Users</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {users.length} registered {users.length === 1 ? "user" : "users"}
        </p>
      </div>

      {users.length === 0 ? (
        <p className="text-muted-foreground">No users found.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Registered</TableHead>
              <TableHead>Last Login</TableHead>
              <TableHead className="text-right">Jobs</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="font-medium">{u.email}</TableCell>
                <TableCell>{formatDate(u.created_at)}</TableCell>
                <TableCell>{formatDateTime(u.last_login)}</TableCell>
                <TableCell className="text-right">{u.job_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
