import { useState } from "react";

export default function App() {
  const [log, setLog] = useState([]);

  async function sendCommand(msg) {
    const res = await fetch("http://localhost:8000/intent", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ message: msg, chat_history: [] })
    });
    const data = await res.json();
    setLog(l => [...l, "> " + msg, JSON.stringify(data)]);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <button>Create Card</button>
        <button>Maps</button>
        <button>Knowledge</button>
        <button>Settings</button>
      </aside>

      <main className="main">
        <div className="log">
          {log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
        <input
          placeholder="Type a command..."
          onKeyDown={e => e.key === "Enter" && sendCommand(e.target.value)}
        />
      </main>
    </div>
  );
}
