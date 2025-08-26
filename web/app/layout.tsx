import "./globals.css";
import { Toaster } from "sonner";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PM Agent",
  description: "Project onboarding wizard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Toaster position="top-right" richColors />
        <div className="mx-auto max-w-5xl p-6">{children}</div>
      </body>
    </html>
  );
}
