"use client"

import Link from "next/link"
import useCameras from "../../hooks/useCameras"
import CameraCard from "../../components/cards/CameraCard"


export default function CamerasPage() {
    const cameras = useCameras()


    return (
        <div className="flex flex-col gap-4">
            <Link href="/" className="text-slate-400 hover:text-white flex items-center gap-2 text-sm font-medium w-fit">
                ← Back to Dashboard
            </Link>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {cameras.map((cam) => (
                    <CameraCard key={cam.id} camera={cam} />
                ))}
            </div>
        </div>
    )
}