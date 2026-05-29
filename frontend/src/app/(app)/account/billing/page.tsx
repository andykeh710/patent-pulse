"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { billingApi } from "@/lib/api";
import useSWR from "swr";
import type { BillingSubscription, Tier } from "@/lib/types";

const TIER_COLORS: Record<Tier, string> = {
  free: "bg-gray-100 text-gray-700",
  basic: "bg-blue-100 text-blue-700",
  lifetime: "bg-purple-100 text-purple-700",
  enterprise: "bg-amber-100 text-amber-700",
};

const PLANS = [
  {
    tier: "basic" as Tier,
    name: "Basic",
    price: "$8 / year",
    features: ["Unlimited topics", "Unlimited alerts", "CSV exports", "Email support"],
  },
  {
    tier: "lifetime" as Tier,
    name: "Lifetime",
    price: "$108 once",
    features: ["Everything in Basic", "PDF patent reports", "Lifetime access", "No recurring payments"],
  },
  {
    tier: "enterprise" as Tier,
    name: "Enterprise",
    price: "$1,000 / year",
    features: ["Everything in Lifetime", "API access", "Programmatic patent data", "Priority support"],
  },
];

export default function BillingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const { data: sub, mutate } = useSWR<BillingSubscription>(
    isAuthenticated ? "billing-sub" : null,
    () => billingApi.getSubscription()
  );

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>;
  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  const currentTier: Tier = sub?.tier ?? "free";
  const success = searchParams.get("success");
  const canceled = searchParams.get("canceled");

  const handleUpgrade = async (tier: string) => {
    const resp = await billingApi.createCheckoutSession(tier);
    if (resp.checkout_url) {
      window.location.href = resp.checkout_url;
    }
  };

  const handleManage = async () => {
    const resp = await billingApi.createPortalSession();
    if (resp.portal_url) {
      window.location.href = resp.portal_url;
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-bold">Billing</h1>

      {success === "true" && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded">
          Payment received. Your account will update shortly.
        </div>
      )}
      {canceled === "true" && (
        <div className="bg-gray-50 border border-gray-200 text-gray-700 px-4 py-3 rounded">
          Checkout canceled. No charges made.
        </div>
      )}

      {/* Current tier */}
      <div className="border rounded p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Current plan:</span>
          <span className={`px-2 py-0.5 rounded text-xs font-semibold ${TIER_COLORS[currentTier]}`}>
            {currentTier.toUpperCase()}
          </span>
        </div>
        {sub && sub.status && (
          <p className="text-sm text-gray-600">Status: {sub.status}</p>
        )}
        {currentTier === "lifetime" && (
          <p className="text-sm text-gray-600">Lifetime access — no renewal needed.</p>
        )}
        {sub?.current_period_end && currentTier !== "lifetime" && currentTier !== "free" && (
          <p className="text-sm text-gray-600">
            {sub.cancel_at_period_end ? "Cancels on " : "Renews on "}
            {new Date(sub.current_period_end).toLocaleDateString()}
          </p>
        )}
        {sub?.cancel_at_period_end && (
          <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
            Your subscription is set to cancel at the end of the current period.
          </div>
        )}
        {currentTier === "free" && (
          <p className="text-sm text-gray-500">Upgrade to unlock more features.</p>
        )}

        {(currentTier === "basic" || currentTier === "enterprise") && sub?.stripe_customer_id && (
          <button
            onClick={handleManage}
            className="mt-2 px-4 py-2 bg-gray-700 text-white rounded text-sm hover:bg-gray-800"
          >
            Manage Subscription (Stripe Portal)
          </button>
        )}
      </div>

      {/* Upgrade cards */}
      <h2 className="text-lg font-semibold">Upgrade</h2>
      <div className="grid gap-4">
        {PLANS.filter((p) => {
          const order = ["free", "basic", "lifetime", "enterprise"];
          return order.indexOf(p.tier) > order.indexOf(currentTier);
        }).map((plan) => (
          <div key={plan.tier} className="border rounded p-4 flex justify-between items-start">
            <div>
              <h3 className="font-semibold">{plan.name}</h3>
              <p className="text-lg font-bold">{plan.price}</p>
              <ul className="text-sm text-gray-600 mt-1 space-y-0.5">
                {plan.features.map((f) => (
                  <li key={f}>• {f}</li>
                ))}
              </ul>
            </div>
            <button
              onClick={() => handleUpgrade(plan.tier)}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            >
              Upgrade
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
