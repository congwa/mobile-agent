import { cn } from "@/utils/tailwind";

interface ConnectionIndicatorProps {
  connected: boolean;
  size?: "sm" | "md" | "lg";
}

export default function ConnectionIndicator({
  connected,
  size = "md",
}: ConnectionIndicatorProps) {
  const sizeClasses = {
    sm: "h-2 w-2",
    md: "h-2.5 w-2.5",
    lg: "h-3 w-3",
  };

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          "rounded-full",
          sizeClasses[size],
          connected
            ? "bg-green-500 shadow-[var(--glow-connected)]"
            : "bg-red-500 shadow-[var(--glow-disconnected)]"
        )}
      />
      {size !== "sm" && (
        <span className="text-xs text-muted-foreground">
          {connected ? "已连接" : "未连接"}
        </span>
      )}
    </span>
  );
}
