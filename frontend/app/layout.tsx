import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aether — Autonomous AI Research Persona",
  description:
    "An autonomous AI persona that discovers, judges, and publishes AI/tech research posts with no human prompting.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="shell">{children}</div>
      </body>
    </html>
  );
}
