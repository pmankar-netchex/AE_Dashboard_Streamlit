/**
 * Column-level constants mirrored from backend column_meta. Backend remains
 * the source of truth via /api/columns; this set is reused for cells that
 * need the lower_is_better hint without threading it through every prop.
 */
export const LOWER_IS_BETTER = new Set<string>(["S1-COL-N"]);
