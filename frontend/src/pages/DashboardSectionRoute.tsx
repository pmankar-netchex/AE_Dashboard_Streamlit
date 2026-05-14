import { useParams } from "@tanstack/react-router";
import { SectionTable } from "@/components/dashboard/SectionTable";
import { useColumnMeta, useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";
import { sectionBySlug } from "@/lib/sections";

export function DashboardSectionRoute() {
  const params = useParams({ strict: false }) as { slug?: string };
  const def = params.slug ? sectionBySlug(params.slug) : undefined;
  const { filters } = useFilters();
  const cols = useColumnMeta();
  const dash = useDashboard(filters);

  if (!def) {
    return (
      <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
        Unknown section.
      </div>
    );
  }

  if (dash.isLoading || cols.isLoading) {
    return (
      <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
        Loading {def.label}…
      </div>
    );
  }

  if (!dash.data || !cols.data) return null;

  const section = cols.data.sections.find((s) => s.key === def.key);
  if (!section) {
    return (
      <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
        Section "{def.key}" not found in column metadata.
      </div>
    );
  }

  return (
    <SectionTable
      section={section}
      columns={cols.data.columns.filter((c) => c.section === def.key)}
      rows={dash.data.rows}
    />
  );
}
