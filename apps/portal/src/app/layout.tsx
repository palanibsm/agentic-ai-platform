import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/sidebar";
import { UserContextProvider } from "@/components/user-context";

export const metadata: Metadata = {
  title: "Agentic AI Platform",
  description: "Enterprise AI assistant — Singapore Bank",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-white">
        <Providers>
          <UserContextProvider>
            <div className="flex min-h-screen">
              <Sidebar />
              <main className="flex-1 min-w-0 overflow-auto">
                {children}
              </main>
            </div>
          </UserContextProvider>
        </Providers>
      </body>
    </html>
  );
}
