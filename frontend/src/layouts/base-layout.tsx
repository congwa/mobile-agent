import type React from "react";
import DragWindowRegion from "@/components/drag-window-region";
import AppSidebar from "@/components/layout/app-sidebar";

export default function BaseLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col bg-background">
      <DragWindowRegion title="Mobile Agent" />
      <div className="flex flex-1 overflow-hidden">
        <AppSidebar />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
