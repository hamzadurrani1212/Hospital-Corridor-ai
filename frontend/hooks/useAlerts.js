import { useEffect, useState } from "react"
import { fetchAlerts } from "../services/alertService"


export default function useAlerts() {
const [alerts, setAlerts] = useState([])
const [loading, setLoading] = useState(true)


useEffect(() => {
fetchAlerts().then((data) => {
setAlerts(data)
setLoading(false)
})
}, [])


return { alerts, loading }
}