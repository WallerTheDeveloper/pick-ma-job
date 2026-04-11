/** Check-email page — shown after magic link is sent. */

import { Link, useLocation } from "react-router";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export function CheckEmailPage() {
  const location = useLocation();
  const email = (location.state as { email?: string } | null)?.email;

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="fixed top-4 right-4">
        <ThemeToggle />
      </div>
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Check your email</CardTitle>
          <CardDescription>
            {email ? (
              <>We sent a sign-in link to <strong>{email}</strong>.</>
            ) : (
              "We sent you a sign-in link."
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground">
            Click the link in your email to sign in. The link expires in 15
            minutes.
          </p>
          <Link to="/login" className="block">
            <Button variant="outline" className="w-full">
              Back to login
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
