/**
 * URL-safe slugs for the 5 dashboard sections. Section keys come from the
 * backend column registry; slugs are stable strings used in route params.
 */

export interface SectionDef {
  slug: string;
  key: string;
  label: string;
}

export const SECTION_DEFS: SectionDef[] = [
  { slug: "pipeline-quota", key: "Pipeline & Quota", label: "Pipeline & Quota" },
  { slug: "self-gen", key: "Self-Gen Pipeline Creation", label: "Self-Gen Pipeline" },
  { slug: "sdr", key: "SDR Activity", label: "SDR Activity" },
  { slug: "channel", key: "Channel Partners", label: "Channel Partners" },
  { slug: "marketing", key: "Marketing", label: "Marketing" },
];

export function sectionBySlug(slug: string): SectionDef | undefined {
  return SECTION_DEFS.find((s) => s.slug === slug);
}
