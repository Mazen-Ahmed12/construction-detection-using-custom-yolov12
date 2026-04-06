import { useRef, useState } from "react";

export default function App() {
  const [videoFrames, setVideoFrames] = useState([]);
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);

  const uploadVideo = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    await fetch("http://localhost:8000/upload", {
      method: "POST",
      body: formData,
    });

    // connect WebSocket
    if (!wsRef.current) {
      wsRef.current = new WebSocket("ws://localhost:8000/ws/video");

      wsRef.current.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        setVideoFrames([data.frame]); // only latest frame
        setEvents((prev) => [...prev.slice(-50), ...data.events]);
      };
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Real-time Video Detection</h1>
      <input type="file" onChange={uploadVideo} />
      <div className="mt-4 flex gap-4">
        <div>
          {videoFrames.length > 0 && (
            <img
              src={`data:image/jpeg;base64,${videoFrames[0]}`}
              alt="frame"
              width="640"
              height="360"
            />
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold">Detection Events</h2>
          <ul className="max-h-[360px] overflow-auto border p-2">
            {events.map((e, idx) => (
              <li key={idx} className="border-b p-1">
                Frame:{e.frame_id} | ID:{e.equipment_id} | Type:{e.equipment_type} | Activity:{e.activity}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}