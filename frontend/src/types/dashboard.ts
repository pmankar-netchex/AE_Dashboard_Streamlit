export type FormatHint = "currency" | "percent" | "number";

export interface ColumnMeta {
  col_id: string;
  display_name: string;
  section: string;
  description: string;
  time_filter: boolean;
  computed: boolean;
  blocked: boolean;
  aggregation: string;
  format: FormatHint;
  lower_is_better: boolean;
}

export interface SectionMeta {
  key: string;
  display_name: string;
}

export interface KpiSpec {
  col_id: string;
  is_average: boolean;
  display_name: string;
  format: FormatHint;
}

export interface AllSourceSummarySpec {
  label: string;
  pipeline_col: string;
  bookings_col: string;
}

export interface ColumnsResponse {
  columns: ColumnMeta[];
  sections: SectionMeta[];
  kpi_row_1: KpiSpec[];
  kpi_row_2: KpiSpec[];
  all_source_summary: AllSourceSummarySpec[];
  total_bookings_col: string;
}

export interface AERow {
  ae_id: string;
  ae_name: string;
  ae_email: string;
  ae_manager: string;
  values: Record<string, number | null>;
}

export interface KpiValue {
  col_id: string;
  is_average: boolean;
  display_name: string;
  format: FormatHint;
  value: number | null;
}

export interface AllSourceSummaryCell {
  label: string;
  pipeline: number | null;
  bookings: number | null;
}

export interface AllSourceSummaryRow {
  ae_id: string;
  ae_name: string;
  ae_manager: string;
  total_pipeline: number | null;
  total_bookings: number | null;
  sources: AllSourceSummaryCell[];
}

export interface DashboardResponse {
  rows: AERow[];
  all_source_summary: AllSourceSummaryRow[];
  kpi_row_1: KpiValue[];
  kpi_row_2: KpiValue[];
  period_start: string;
  period_end: string;
  fetched_at: number;
}

export interface AEDrillDownResponse {
  ae_id: string;
  ae_name: string;
  ae_email: string;
  ae_manager: string;
  sdr_name: string;
  sdr_email: string;
  values: Record<string, number | null>;
  all_source_summary: AllSourceSummaryRow;
  kpi_row_1: KpiValue[];
  kpi_row_2: KpiValue[];
  period_start: string;
  period_end: string;
  fetched_at: number;
}

export interface ManagerOption {
  name: string;
}

export interface AEOption {
  id: string;
  name: string;
  email: string;
  manager?: string | null;
}

export type TimePreset =
  | "this_week"
  | "last_week"
  | "this_month"
  | "last_month"
  | "custom";

export interface TimePresetOption {
  key: TimePreset;
  display_name: string;
}
