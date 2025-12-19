import { useEffect, useState, useCallback } from "react";
import { getPersons, getPeopleCount } from "../services/eventService";

/**
 * Hook for fetching and managing event/person data
 */
export default function useEvents() {
    const [persons, setPersons] = useState([]);
    const [peopleCount, setPeopleCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [personsData, count] = await Promise.all([
                getPersons(),
                getPeopleCount(),
            ]);

            setPersons(personsData);
            setPeopleCount(count);
        } catch (err) {
            console.error("Error fetching events data:", err);
            setError(err.message || "Failed to load data");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Refetch function for manual refresh
    const refetch = () => {
        fetchData();
    };

    return {
        persons,
        peopleCount,
        loading,
        error,
        refetch,
    };
}
