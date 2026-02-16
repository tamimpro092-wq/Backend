import "./globals.css";
import Nav from "./components/Nav";

export const metadata = {
  title: "JARVIS Mode",
  description: "Overnight E-commerce Autopilot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex">
          {/* Desktop sidebar */}
          <Nav />

          {/* Main area */}
          <div className="flex-1">
            {/* Mobile top bar */}
            <div className="md:hidden neon-card border-x-0 border-t-0 rounded-none p-3">
              <div className="flex items-center justify-between">
                <div className="font-semibold">
                  JARVIS<span className="text-[color:var(--cyan)]">.AI</span>
                </div>
                <div className="text-xs text-[color:var(--muted)]">Menu in sidebar (desktop)</div>
              </div>
            </div>

            <main className="max-w-6xl mx-auto p-4 md:p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
