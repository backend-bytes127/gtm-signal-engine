import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const TIER_STYLES: Record<string, string> = {
  hot: "bg-red-100 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800",
  warm: "bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-300 dark:border-orange-800",
  watch: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800",
  cold: "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
};

export function TierBadge({ tier }: { tier: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("text-xs font-medium uppercase", TIER_STYLES[tier])}
    >
      {tier}
    </Badge>
  );
}
