import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TBCare | Administrative Evidence Workspace",
  description: "Synthetic TB-program administrative evidence review demo. Not a clinical decision system.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body>{children}</body></html>;
}
