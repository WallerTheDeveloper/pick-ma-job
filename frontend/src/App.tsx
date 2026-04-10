import { BrowserRouter, Route, Routes } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProtectedRoute } from "@/components/protected-route";
import { AppShell } from "@/components/layout/app-shell";
import { DashboardPage } from "@/pages/dashboard";
import { ResultsPage } from "@/pages/results";
import { ProfilePage } from "@/pages/profile";
import { SearchConfigPage } from "@/pages/search-config";
import { AdminPage } from "@/pages/admin";
import { LoginPage } from "@/pages/login";
import { CheckEmailPage } from "@/pages/check-email";
import { LandingPage } from "@/pages/landing";
import { Toaster } from "@/components/ui/sonner";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route index element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/check-email" element={<CheckEmailPage />} />

          {/* Protected routes — redirect to / if not authenticated */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="results" element={<ResultsPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="search-config" element={<SearchConfigPage />} />
              <Route path="admin" element={<AdminPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster />
    </QueryClientProvider>
  );
}
