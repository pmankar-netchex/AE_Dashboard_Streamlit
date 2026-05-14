import { AEMultiSelect } from "./AEMultiSelect";
import { ManagerSelect } from "./ManagerSelect";
import { RefreshButton } from "./RefreshButton";
import { TimePeriodPicker } from "./TimePeriodPicker";

export function FilterBar() {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center gap-4 border-b border-border bg-background/95 px-6 py-2 backdrop-blur">
      <ManagerSelect />
      <AEMultiSelect />
      <TimePeriodPicker />
      <div className="ml-auto">
        <RefreshButton />
      </div>
    </div>
  );
}
