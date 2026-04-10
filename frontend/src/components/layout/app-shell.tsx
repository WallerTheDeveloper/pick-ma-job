import { NavLink, Outlet } from "react-router";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/results", label: "Results" },
  { to: "/profile", label: "Profile" },
  { to: "/search-config", label: "Search Config" },
] as const;

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-sidebar-accent text-sidebar-accent-foreground"
      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
  }`;

export function AppShell() {
  const { user, logout, logoutStatus } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 border-r border-border bg-sidebar text-sidebar-foreground flex flex-col">
        <div className="px-4 py-5">
          <h1 className="text-lg font-semibold tracking-tight">Pick Ma Job</h1>
        </div>
        <Separator />
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={navLinkClass}
            >
              {label}
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink to="/admin" className={navLinkClass}>
              Admin
            </NavLink>
          )}
        </nav>
        <Separator />
        <div className="px-3 py-4 space-y-2">
          {user && (
            <p className="truncate px-3 text-xs text-sidebar-foreground/60">
              {user.email}
            </p>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => logout()}
            disabled={logoutStatus === "pending"}
          >
            {logoutStatus === "pending" ? "Signing out..." : "Sign out"}
          </Button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-x-hidden p-6">
        <Outlet />
      </main>
    </div>
  );
}
