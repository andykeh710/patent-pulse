import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AccountDropdown } from "./AccountDropdown";
import { useAuth } from "@/lib/AuthContext";
import { useRouter } from "next/navigation";

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn(),
}));

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

describe("AccountDropdown", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("uses backend logout so the HttpOnly session cookie is cleared", async () => {
    const logout = jest.fn().mockResolvedValue(undefined);
    const push = jest.fn();
    (useAuth as jest.Mock).mockReturnValue({
      user: { id: "local-user", email: "test@example.com", displayName: "Test User" },
      isAuthenticated: true,
      logout,
    });
    (useRouter as jest.Mock).mockReturnValue({ push });

    render(<AccountDropdown />);

    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
    expect(push).toHaveBeenCalledWith("/login");
  });
});
