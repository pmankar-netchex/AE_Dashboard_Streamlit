import { useQuery } from "@tanstack/react-query";
import { fetchMe, type MeResponse } from "@/api/me";

export function useMe() {
  return useQuery<MeResponse>({
    queryKey: ["me"],
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
  });
}
