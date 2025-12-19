import api from "./api";

/**
 * Event Service - handles person detection, search, and event data
 */

/**
 * Search for matching persons by uploading an image
 * @param {File} file - Image file to search with
 * @param {number} topK - Number of results to return
 */
export const searchByImage = async (file, topK = 5) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("top_k", topK);

    const res = await api.post("/search/image", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });
    return res.data;
};

/**
 * Search for matching persons by text description
 * @param {string} query - Text description to search with
 * @param {number} topK - Number of results to return
 */
export const searchByText = async (query, topK = 5) => {
    const formData = new FormData();
    formData.append("query", query);
    formData.append("top_k", topK);

    const res = await api.post("/search/text", formData);
    return res.data;
};

/**
 * Get count of people detected today
 */
export const getPeopleCount = async () => {
    try {
        const res = await api.get("/events/people");
        return res.data.count;
    } catch (error) {
        console.error("Failed to get people count:", error);
        return 0;
    }
};

/**
 * Get list of detected persons from the database
 * Note: This reuses the staff list endpoint since persons are stored similarly
 */
export const getPersons = async () => {
    try {
        const res = await api.get("/staff/");
        return res.data;
    } catch (error) {
        console.error("Failed to get persons:", error);
        return [];
    }
};
