import axios from "axios"

// API base URL for backend - explicitly set to prevent env variable issues
const API_BASE_URL = "http://localhost:8000/api";

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000, // 10 seconds
})

// Debug: log the baseURL being used
console.log("[API] Using baseURL:", API_BASE_URL);

export default api