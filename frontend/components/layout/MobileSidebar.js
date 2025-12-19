"use client"

import Link from "next/link"
import { useAuth } from "../common/AuthProvider"

export default function MobileSidebar({ open, onClose }) {
  const { user } = useAuth()
  if (!open || !user) return null

  const menu = [
    { name: "Dashboard", path: "/dashboard", roles: ["admin", "operator", "viewer"] },
    { name: "Cameras", path: "/cameras", roles: ["admin", "operator"] },
    { name: "Alerts", path: "/alerts", roles: ["admin", "operator"] },
    { name: "Events", path: "/events", roles: ["admin", "operator", "viewer"] },
  ]

  return (
    <div className="fixed inset-0 z-50 bg-black/40">
      <aside className="w-64 bg-white h-full p-4">
        <button onClick={onClose} className="mb-4 text-sm text-gray-500">
          ✖ Close
        </button>

        {menu
          .filter(m => m.roles.includes(user.role))
          .map(m => (
            <Link
              key={m.name}
              href={m.path}
              onClick={onClose}
              className="block py-2"
            >
              {m.name}
            </Link>
          ))}
      </aside>
    </div>
  )
}
