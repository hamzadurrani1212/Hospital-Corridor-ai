import { useEffect, useRef } from "react"


export default function useSocket(onMessage) {
    const socketRef = useRef(null)


    useEffect(() => {
        socketRef.current = new WebSocket(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/alerts')


        socketRef.current.onmessage = (event) => {
            const data = JSON.parse(event.data)
            onMessage(data)
        }


        return () => socketRef.current.close()
    }, [onMessage])
}