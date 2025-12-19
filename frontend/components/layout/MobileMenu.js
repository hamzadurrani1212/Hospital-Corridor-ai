"use client"


import Link from "next/link"


const menu = [
{ name: "Dashboard", path: "/dashboard" },
{ name: "Cameras", path: "/cameras" },
{ name: "Alerts", path: "/alerts" },
{ name: "Events", path: "/events" },
{ name: "Settings", path: "/settings" },
]


export default function MobileMenu({ open, onClose }) {
if (!open) return null


return (
<div className="fixed inset-0 z-50 bg-black/40 lg:hidden">
<div className="absolute left-0 top-0 h-full w-64 bg-white shadow">
<div className="h-16 flex items-center justify-between px-4 border-b">
<span className="font-bold">🏥 Hospital AI</span>
<button onClick={onClose}>✕</button>
</div>


<nav className="p-4 space-y-2">
{menu.map((item) => (
<Link
key={item.name}
href={item.path}
onClick={onClose}
className="block rounded px-3 py-2 text-gray-700 hover:bg-blue-50"
>
{item.name}
</Link>
))}
</nav>
</div>
</div>
)
}