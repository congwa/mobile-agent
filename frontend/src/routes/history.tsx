import { createFileRoute } from "@tanstack/react-router";
import HistoryPage from "@/components/pages/history-page";

function HistoryRoute() {
  return <HistoryPage />;
}

export const Route = createFileRoute("/history")({
  component: HistoryRoute,
});
