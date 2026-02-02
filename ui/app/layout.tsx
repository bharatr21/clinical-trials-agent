import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clinical Trials Agent",
  description: "Query clinical trials data using natural language",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
