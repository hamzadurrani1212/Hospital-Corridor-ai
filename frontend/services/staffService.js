import api from "./api";

/**
 * Staff Service - handles staff registration and management
 */

/**
 * Register a new authorized staff member with 3 angles
 * @param {Object} staffData - Staff registration data
 * @param {string} staffData.name - Staff member name
 * @param {string} staffData.role - Role (Doctor, Nurse, Security, etc.)
 * @param {string} staffData.department - Department name
 * @param {File} staffData.frontImage - Front face image (Required)
 * @param {File} staffData.leftImage - Left profile image (Optional)
 * @param {File} staffData.rightImage - Right profile image (Optional)
 */
export const registerStaff = async ({ name, role, department, frontImage, leftImage, rightImage }) => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("role", role);
    formData.append("department", department);

    if (frontImage) formData.append("front_image", frontImage);
    if (leftImage) formData.append("left_image", leftImage);
    if (rightImage) formData.append("right_image", rightImage);

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
