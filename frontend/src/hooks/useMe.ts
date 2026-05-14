import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { fetchMe, type MeResponse } from "@/api/me";

export function useMe() {
  return useQuery<MeResponse, ApiError>({
    queryKey: ["me"],
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
    // Don't retry on auth/access errors — they won't fix themselves.
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        return false;
      }
      return failureCount < 1;
    },
  });
}
