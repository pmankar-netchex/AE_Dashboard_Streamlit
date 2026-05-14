import { ReadOnlyGate } from "@/components/auth/ReadOnlyGate";
import { SalesforceStatusCard } from "@/components/config/salesforce/SalesforceStatusCard";

export function ConfigSalesforceRoute() {
  return (
    <ReadOnlyGate>
      <SalesforceStatusCard />
    </ReadOnlyGate>
  );
}
