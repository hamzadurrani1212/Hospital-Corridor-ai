import api from "./api"


export const fetchCameras = async () => {
    try {
        const res = await api.get("/cameras")
        return res.data
    } catch (error) {
        console.error("Error fetching cameras:", error)
        throw error
    }
}