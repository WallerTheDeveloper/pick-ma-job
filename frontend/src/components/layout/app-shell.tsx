import { NavLink, Outlet } from "react-router";
import { LayoutDashboard, FileSearch, User, Settings, Shield, LogOut } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/results", label: "Results", icon: FileSearch },
  { to: "/profile", label: "Profile", icon: User },
  { to: "/search-config", label: "Search Config", icon: Settings },
] as const;

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-sidebar-primary text-sidebar-primary-foreground"
      : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
  }`;

export function AppShell() {
  const { user, logout, logoutStatus } = useAuth();

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col">
        <div className="px-4 py-5">
          <h1 className="text-lg font-semibold tracking-tight text-sidebar-primary">Pick Ma Job</h1>
        </div>
        <Separator className="bg-sidebar-border" />
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={navLinkClass}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink to="/admin" className={navLinkClass}>
              <Shield className="h-4 w-4 shrink-0" />
              Admin
            </NavLink>
          )}
        </nav>
        <Separator className="bg-sidebar-border" />
        <div className="px-3 py-4 space-y-2">
          {user && (
            <p className="truncate px-3 text-xs text-sidebar-foreground/60">
              {user.email}
            </p>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-sidebar-foreground/70 hover:text-sidebar-foreground"
            onClick={() => logout()}
            disabled={logoutStatus === "pending"}
          >
            <LogOut className="h-4 w-4" />
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
