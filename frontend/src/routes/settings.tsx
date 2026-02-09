import { createFileRoute } from "@tanstack/react-router";
import SettingsPage from "@/components/pages/settings-page";

function SettingsRoute() {
  return <SettingsPage />;
}

export const Route = createFileRoute("/settings")({
  component: SettingsRoute,
});
