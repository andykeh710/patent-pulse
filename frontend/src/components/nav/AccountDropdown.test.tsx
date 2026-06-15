import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AccountDropdown } from "./AccountDropdown";
import { useAuth } from "@/lib/AuthContext";

const pushMock = jest.fn();
const logoutMock = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn(),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe("AccountDropdown", () => {
  beforeEach(() => {
    pushMock.mockClear();
    logoutMock.mockClear();
    mockedUseAuth.mockReturnValue({
      user: {
        id: "user-1",
        email: "test@example.com",
        displayName: "Test User",
      },
      isLoading: false,
      isAuthenticated: true,
      logout: logoutMock,
    });
  });

  it("logs out through the auth context before navigating to login", async () => {
    render(<AccountDropdown />);

    fireEvent.click(screen.getByRole("button", { name: /t/i }));
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => {
      expect(logoutMock).toHaveBeenCalledTimes(1);
    });
    expect(pushMock).toHaveBeenCalledWith("/login");
  });
});
