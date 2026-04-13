/** Subtle version badge shown in the app sidebar footer. */

import { useVersion } from "@/hooks/use-version";

export function VersionFooter() {
  const version = useVersion();

  if (!version) return null;

  return (
    <p className="px-3 text-xs text-sidebar-foreground/40 select-none">
      v{version}
    </p>
  );
}
