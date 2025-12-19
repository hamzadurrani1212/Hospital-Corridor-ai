"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    FiGrid,
    FiCamera,
    FiActivity,
    FiSettings,
    FiBell
} from "react-icons/fi";

const NAV_ITEMS = [
    { href: "/", icon: FiGrid, label: "Dashboard" },
    { href: "/cameras", icon: FiCamera, label: "Cameras" },
    { href: "/events", icon: FiActivity, label: "Events" }, // Using Activity for pulse icon lookalike
    { href: "/alerts", icon: FiBell, label: "Alerts" },
    { href: "/settings", icon: FiSettings, label: "Settings" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="fixed left-0 top-0 h-screen w-16 bg-sidebar border-r border-slate-800 flex flex-col items-center py-6 z-50">
            <nav className="flex-1 flex flex-col gap-6 w-full items-center">
                {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
                    const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={`p-3 rounded-xl transition-all duration-200 group relative
                ${isActive
                                    ? "bg-accent/10 text-accent"
                                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                                }`}
                        >
                            <Icon size={24} />

                            {/* Tooltip */}
                            <span className="absolute left-14 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                                {label}
                            </span>
                        </Link>
                    );
                })}
            </nav>
        </aside>
    );
}
