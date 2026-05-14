import { useQuery } from "@tanstack/react-query";
import { Lock, LogOut, Mail } from "lucide-react";
import { Logo } from "@/components/layout/Logo";

interface EasyAuthClaim {
  typ?: string;
  val?: string;
}
interface EasyAuthMe {
  user_id?: string;
  user_claims?: EasyAuthClaim[];
  identity_provider?: string;
}

/**
 * Easy Auth on Container Apps exposes /.auth/me — JSON principal info for
 * the signed-in user. We use it on the NoAccess page so we can show the
 * exact email the user is signed in as (helpful when asking an admin to
 * grant them access).
 */
function useEasyAuthMe() {
  return useQuery<EasyAuthMe | null>({
    queryKey: ["easy-auth-me"],
    queryFn: async () => {
      try {
        const res = await fetch("/.auth/me", {
          credentials: "include",
          headers: { Accept: "application/json" },
        });
        if (!res.ok) return null;
        const body = await res.json();
        // Container Apps returns an array of identities; we take the first.
        return Array.isArray(body) ? (body[0] ?? null) : body;
      } catch {
        return null;
      }
    },
    staleTime: 60_000,
    retry: false,
  });
}

function pickClaim(me: EasyAuthMe | null | undefined, names: string[]): string | null {
  if (!me?.user_claims) return null;
  for (const name of names) {
    const c = me.user_claims.find((c) => c.typ === name);
    if (c?.val) return c.val;
  }
  return null;
}

export function NoAccessPage() {
  const { data: ea } = useEasyAuthMe();
  const email =
    pickClaim(ea, [
      "emails",
      "email",
      "preferred_username",
      "upn",
      "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    ]) ||
    ea?.user_id ||
    null;
  const name = pickClaim(ea, ["name", "given_name"]);

  const bodyLines = [
    "Hello,",
    "",
    `I'm signed in as ${email ?? "(my Netchex Microsoft account)"} but I don't have access to the AE Performance Dashboard yet.`,
    "",
    "Could you add me as a user? Thanks.",
  ].join("\n");
  const mailto = `mailto:pmankar@netchexonline.com?subject=${encodeURIComponent(
    "AE Dashboard access request",
  )}&body=${encodeURIComponent(bodyLines)}`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-background p-8 shadow-sm">
        <div className="flex justify-center">
          <Logo size={48} />
        </div>

        <div className="mt-6 flex items-center justify-center gap-2 text-amber-700">
          <Lock className="h-5 w-5" />
          <h1 className="text-lg font-semibold">You don't have access yet</h1>
        </div>

        <p className="mt-3 text-center text-sm text-muted-foreground">
          You signed in successfully, but your account hasn't been added to the
          AE Dashboard user list. An admin needs to grant you access before you
          can view the dashboard.
        </p>

        <div className="mt-5 rounded-md border border-border bg-muted/40 px-4 py-3 text-sm">
          <div className="text-xs text-muted-foreground">Signed in as</div>
          <div className="mt-0.5 break-all font-medium">{email ?? "—"}</div>
          {name && (
            <div className="mt-0.5 text-xs text-muted-foreground">{name}</div>
          )}
        </div>

        <div className="mt-5 flex flex-col gap-2">
          <a
            href={mailto}
            className="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          >
            <Mail className="h-4 w-4" />
            Request access
          </a>
          <a
            href="/.auth/logout"
            className="inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-background px-3 py-2 text-sm hover:bg-accent"
          >
            <LogOut className="h-4 w-4" />
            Sign in as a different user
          </a>
        </div>

        <p className="mt-5 text-center text-[11px] text-muted-foreground">
          Once added, refresh this page — you'll go straight to the dashboard.
        </p>
      </div>
    </div>
  );
}
