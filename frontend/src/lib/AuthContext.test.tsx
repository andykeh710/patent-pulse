import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "./AuthContext";
import { authApi } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  authApi: {
    me: jest.fn(),
    logout: jest.fn(),
  },
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function Probe() {
  const { user, refreshUser } = useAuth();
  return (
    <div>
      <span>{user?.email ?? "signed-out"}</span>
      <button type="button" onClick={() => void refreshUser()}>
        refresh
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("keeps the newest authenticated refresh when an older unauthenticated request finishes later", async () => {
    const initial = deferred<never>();
    (authApi.me as jest.Mock)
      .mockReturnValueOnce(initial.promise)
      .mockResolvedValueOnce({
        id: "local-user",
        email: "test@example.com",
        display_name: "Test User",
      });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "refresh" }));

    await waitFor(() => expect(screen.getByText("test@example.com")).toBeInTheDocument());

    await act(async () => {
      initial.reject(new Error("stale 401"));
      await initial.promise.catch(() => undefined);
    });

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("does not restore the user when a pending refresh resolves after logout", async () => {
    const pendingRefresh = deferred<{
      id: string;
      email: string;
      display_name: string;
    }>();
    (authApi.me as jest.Mock).mockReturnValueOnce(pendingRefresh.promise);
    (authApi.logout as jest.Mock).mockResolvedValue({ ok: true });

    function LogoutProbe() {
      const { user, logout } = useAuth();
      return (
        <div>
          <span>{user?.email ?? "signed-out"}</span>
          <button type="button" onClick={() => void logout()}>
            logout
          </button>
        </div>
      );
    }

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: "logout" }));

    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1));

    await act(async () => {
      pendingRefresh.resolve({
        id: "local-user",
        email: "test@example.com",
        display_name: "Test User",
      });
      await pendingRefresh.promise;
    });

    expect(screen.getByText("signed-out")).toBeInTheDocument();
  });
});
