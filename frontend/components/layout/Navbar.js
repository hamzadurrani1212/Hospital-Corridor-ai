"use client";

import { HiMenu } from "react-icons/hi";

export default function Navbar({ toggleSidebar }) {
  return (
    <header className="flex items-center justify-between h-16 px-4 bg-white border-b shadow-sm">
      {/* Mobile Menu Button */}
      <button
        className="lg:hidden p-2 rounded hover:bg-gray-100 transition"
        onClick={toggleSidebar}
      >
        <HiMenu className="w-6 h-6" />
      </button>

      <h1 className="text-lg font-bold">Hospital Corridor AI</h1>
    </header>
  );
}
