import api from "./api";

/**
 * Staff Service - handles staff registration and management
 */

/**
 * Register a new authorized staff member
 * @param {Object} staffData - Staff registration data
 * @param {string} staffData.name - Staff member name
 * @param {string} staffData.role - Role (Doctor, Nurse, Security, etc.)
 * @param {string} staffData.department - Department name
 * @param {File} staffData.image - Staff member image file
 */
export const registerStaff = async ({ name, role, department, image }) => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("role", role);
    formData.append("department", department);
    formData.append("image", image);

    const res = await api.post("/staff/register", formData, {
        headers: {
            "Content-Type": "multipart/form-data",
        },
    });
    return res.data;
};

/**
 * Get list of all registered staff
 */
export const getStaffList = async () => {
    try {
        const res = await api.get("/staff/");
        return res.data;
    } catch (error) {
        console.error("Failed to get staff list:", error);
        return [];
    }
};

/**
 * Get a specific staff member by ID
 * @param {string} staffId - Staff ID
 */
export const getStaffById = async (staffId) => {
    const res = await api.get(`/staff/${staffId}`);
    return res.data;
};

/**
 * Delete a staff member
 * @param {string} staffId - Staff ID to delete
 */
export const deleteStaff = async (staffId) => {
    const res = await api.delete(`/staff/${staffId}`);
    return res.data;
};
