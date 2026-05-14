import { ReadOnlyGate } from "@/components/auth/ReadOnlyGate";
import { UserList } from "@/components/config/users/UserList";

export function ConfigUsersRoute() {
  return (
    <ReadOnlyGate>
      <UserList />
    </ReadOnlyGate>
  );
}
