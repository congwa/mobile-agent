import { createFileRoute } from "@tanstack/react-router";
import DashboardPage from "@/components/pages/dashboard-page";

function HomePage() {
  return <DashboardPage />;
}

export const Route = createFileRoute("/")({
  component: HomePage,
});
