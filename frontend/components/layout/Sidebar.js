"use client";

import Link from "next/link";
import { useAuth } from "../common/AuthProvider";

export default function Sidebar({ isMobile, onClose }) {
  const { user } = useAuth();
  if (!user) return null;

  const menu = [
    { name: "Dashboard", path: "/dashboard", roles: ["admin", "operator", "viewer"] },
    { name: "Cameras", path: "/cameras", roles: ["admin", "operator"] },
    { name: "Alerts", path: "/alerts", roles: ["admin", "operator"] },
    { name: "Events", path: "/events", roles: ["admin", "operator", "viewer"] },
    { name: "Settings", path: "/settings", roles: ["admin"] },
  ];

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-64 bg-white border-r flex-col">
        <div className="h-16 flex items-center justify-center font-bold border-b">
          🏥 Hospital AI
        </div>
        <nav className="flex-1 p-4 space-y-2">
          {menu
            .filter((item) => item.roles.includes(user.role))
            .map((item) => (
              <Link
                key={item.name}
                href={item.path}
                className="block rounded px-3 py-2 hover:bg-blue-50"
              >
                {item.name}
              </Link>
            ))}
        </nav>
      </aside>

      {/* Mobile Sidebar */}
      {isMobile && (
        <aside className="fixed left-0 top-0 h-full w-64 bg-white shadow-xl z-50 p-4 animate-slide-in">
          <div className="h-16 flex items-center justify-between font-bold border-b">
            🏥 Hospital AI
            <button onClick={onClose} className="p-2 rounded hover:bg-gray-100">
              ✖
            </button>
          </div>
          <nav className="mt-4 space-y-2">
            {menu
              .filter((item) => item.roles.includes(user.role))
              .map((item) => (
                <Link
                  key={item.name}
                  href={item.path}
                  className="block rounded px-3 py-2 hover:bg-blue-50"
                  onClick={onClose}
                >
                  {item.name}
                </Link>
              ))}
          </nav>
        </aside>
      )}
    </>
  );
}
