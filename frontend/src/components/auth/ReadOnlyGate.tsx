import { createContext, type ReactNode, useContext } from "react";
import { useMe } from "@/hooks/useMe";

const ReadOnlyContext = createContext(false);

export function ReadOnlyGate({ children }: { children: ReactNode }) {
  const { data: me } = useMe();
  const readOnly = me?.role !== "admin";
  return (
    <ReadOnlyContext.Provider value={readOnly}>{children}</ReadOnlyContext.Provider>
  );
}

export function useReadOnly(): boolean {
  return useContext(ReadOnlyContext);
}
