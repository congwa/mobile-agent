import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Smartphone,
  History,
  Settings,
  Zap,
} from "lucide-react";
import { cn } from "@/utils/tailwind";

const NAV_ITEMS = [
  { to: "/", label: "主控台", icon: LayoutDashboard },
  { to: "/devices", label: "设备管理", icon: Smartphone },
  { to: "/history", label: "历史记录", icon: History },
  { to: "/settings", label: "设置", icon: Settings },
] as const;

export default function AppSidebar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  return (
    <aside className="flex w-16 flex-col items-center border-r border-border bg-card py-4 gap-2">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
        <Zap className="h-5 w-5 text-primary" />
      </div>
      <nav className="flex flex-1 flex-col items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.to === "/" ? currentPath === "/" : currentPath.startsWith(item.to);
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "group relative flex h-10 w-10 items-center justify-center rounded-lg transition-colors duration-200 cursor-pointer",
                isActive
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="absolute left-full ml-2 hidden rounded-md bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md group-hover:block whitespace-nowrap z-50">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
