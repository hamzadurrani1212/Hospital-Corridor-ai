import Sidebar from "@/components/layout/Sidebar";
import "../styles/globals.css";

export const metadata = {
  title: "Hospital Corridor Monitor",
  description: "AI-Powered Safety Monitoring",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground overflow-x-hidden">
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-16 p-6 md:p-8 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
