import { useRef, useState } from "react";

export default function App() {
  const [frame, setFrame] = useState(null);
  const [machines, setMachines] = useState({});
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

    if (!wsRef.current) {
      wsRef.current = new WebSocket("ws://localhost:8000/ws/video");

      wsRef.current.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        setFrame(data.frame);

        const updated = { ...machines };

        data.events.forEach((e) => {
          updated[e.equipment_id] = e;
        });

        setMachines(updated);
      };
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">
        Equipment Utilization Dashboard
      </h1>

      <input type="file" onChange={uploadVideo} />

      <div className="flex gap-6 mt-4">
        {/* Video */}
        <div>
          {frame && (
            <img
              src={`data:image/jpeg;base64,${frame}`}
              width="640"
              alt="video"
            />
          )}
        </div>

        {/* Dashboard */}
        <div className="w-96">
          <h2 className="text-xl font-bold mb-2">Machines</h2>

          {Object.values(machines).map((m) => (
            <div key={m.equipment_id} className="border p-2 mb-2">
              <p><b>ID:</b> {m.equipment_id}</p>
              <p><b>Type:</b> {m.equipment_type}</p>
              <p><b>State:</b> {m.state}</p>
              <p><b>Activity:</b> {m.activity}</p>
              <p><b>Working:</b> {m.working_time.toFixed(1)}s</p>
              <p><b>Idle:</b> {m.idle_time.toFixed(1)}s</p>
              <p><b>Utilization:</b> {m.utilization.toFixed(1)}%</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}