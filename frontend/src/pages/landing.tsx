import { Link } from "react-router";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top navbar */}
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <span className="text-lg font-semibold tracking-tight">Pick Ma Job</span>
        <Link to="/login" className={cn(buttonVariants({ size: "sm" }))}>Sign In</Link>
      </header>

      <main>
        {/* Hero */}
        <section className="px-6 py-24 text-center max-w-3xl mx-auto">
          <h1 className="text-4xl font-bold tracking-tight mb-4">
            Stop scrolling job boards. Start applying to the right ones.
          </h1>
          <p className="text-lg text-muted-foreground mb-8">
            Pick Ma Job scrapes Upwork and LinkedIn, then uses Claude AI to score
            each posting against your profile — so you only see jobs worth your time.
          </p>
          <Link to="/login" className={cn(buttonVariants({ size: "lg" }))}>Get Started</Link>
        </section>

        {/* How it works */}
        <section className="bg-muted/40 px-6 py-20">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold text-center mb-12">How it works</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  step: "1",
                  title: "Set up your profile",
                  description:
                    "Add your skills, experience, and a scoring rubric so the AI knows what matters to you.",
                },
                {
                  step: "2",
                  title: "Configure platform searches",
                  description:
                    "Define search queries and filters for Upwork, LinkedIn, and more platforms as they're added.",
                },
                {
                  step: "3",
                  title: "Get AI-scored job matches",
                  description:
                    "Run the pipeline and get a ranked list of jobs with scores, summaries, and red/green flags.",
                },
              ].map(({ step, title, description }) => (
                <div key={step} className="text-center">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground text-lg font-bold">
                    {step}
                  </div>
                  <h3 className="font-semibold mb-2">{title}</h3>
                  <p className="text-sm text-muted-foreground">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="px-6 py-20">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold text-center mb-12">Why Pick Ma Job</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                {
                  title: "Multi-platform",
                  description:
                    "Pulls from Upwork and LinkedIn today. More platforms coming soon — one dashboard for all your sources.",
                },
                {
                  title: "AI evaluation with Claude",
                  description:
                    "Every job is evaluated by Claude against your specific profile, not generic keyword matching.",
                },
                {
                  title: "Smart scoring and filtering",
                  description:
                    "Jobs are scored 1–10 with detailed explanations. Filter by score, status, and platform to find your best matches.",
                },
                {
                  title: "Saves hours every week",
                  description:
                    "Stop manually scanning hundreds of listings. Run the pipeline and review only the jobs that actually fit.",
                },
              ].map(({ title, description }) => (
                <div key={title} className="rounded-lg border border-border p-6">
                  <h3 className="font-semibold mb-2">{title}</h3>
                  <p className="text-sm text-muted-foreground">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Platforms */}
        <section className="bg-muted/40 px-6 py-16">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-2xl font-semibold mb-8">Supported Platforms</h2>
            <div className="flex justify-center gap-8">
              <div className="rounded-lg border border-border bg-background px-8 py-5 text-sm font-medium">
                Upwork
              </div>
              <div className="rounded-lg border border-border bg-background px-8 py-5 text-sm font-medium">
                LinkedIn
              </div>
            </div>
            <p className="mt-6 text-sm text-muted-foreground">More platforms coming soon</p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-8 text-center text-sm text-muted-foreground">
        <p>
          Ready to get started?{" "}
          <Link to="/login" className="underline underline-offset-4 hover:text-foreground">
            Sign in
          </Link>
        </p>
      </footer>
    </div>
  );
}
