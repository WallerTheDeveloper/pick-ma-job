/** Login page — email form that sends a magic link. */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { requestMagicLink } from "@/api/auth";
import { ApiError } from "@/api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      setError("Please enter your email address.");
      return;
    }

    setIsPending(true);
    try {
      await requestMagicLink(trimmed);
      navigate("/check-email", { state: { email: trimmed } });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Pick Ma Job</CardTitle>
          <CardDescription>
            Enter your email to receive a sign-in link.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                disabled={isPending}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <button
              type="submit"
              className={buttonVariants({ size: "lg", className: "w-full" })}
              disabled={isPending}
            >
              {isPending ? "Sending..." : "Send magic link"}
            </button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
