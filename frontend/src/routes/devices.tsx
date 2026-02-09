import { createFileRoute } from "@tanstack/react-router";
import DevicesPage from "@/components/pages/devices-page";

function Devices() {
  return <DevicesPage />;
}

export const Route = createFileRoute("/devices")({
  component: Devices,
});
