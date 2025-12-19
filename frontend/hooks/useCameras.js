import { useEffect, useState, useCallback } from "react"
import { fetchCameras } from "../services/cameraService"


export default function useCameras() {
    const [cameras, setCameras] = useState([])

    const loadCameras = useCallback(async () => {
        try {
            const data = await fetchCameras()
            setCameras(data || [])
        } catch (error) {
            console.error("Failed to fetch cameras:", error)
            // Return mock data if API fails
            setCameras([
                {
                    id: "0",
                    name: "Main Camera",
                    status: "online",
                    stream_url: "/api/stream/0",
                    location: "Corridor 1"
                }
            ])
        }
    }, [])

    useEffect(() => {
        loadCameras()
    }, [loadCameras])

    return cameras
}