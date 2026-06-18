import { render, waitFor } from "@testing-library/react";
import VerifyPage from "./page";
import { authApi } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import { useRouter, useSearchParams } from "next/navigation";

jest.mock("@/lib/api", () => ({
  authApi: {
    verify: jest.fn(),
  },
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn(),
}));

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}));

describe("VerifyPage", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (useSearchParams as jest.Mock).mockReturnValue(new URLSearchParams("token=abc"));
  });

  it("refreshes auth state before navigating after magic-link verification", async () => {
    const push = jest.fn();
    const refreshUser = jest.fn().mockResolvedValue(undefined);
    (useRouter as jest.Mock).mockReturnValue({ push });
    (useAuth as jest.Mock).mockReturnValue({ refreshUser });
    (authApi.verify as jest.Mock).mockResolvedValue({
      json: async () => ({ ok: true }),
    });
    global.fetch = jest.fn().mockResolvedValue({
      json: async () => ({ onboarded: false }),
    }) as jest.Mock;

    render(<VerifyPage />);

    await waitFor(() => expect(refreshUser).toHaveBeenCalledTimes(1));
    expect(push).toHaveBeenCalledWith("/onboarding");
  });
});
