import { MarketingNav } from "./MarketingNav";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <MarketingNav />
      <main className="pt-16">{children}</main>
    </>
  );
}
