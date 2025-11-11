import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import * as XLSX from "xlsx";
import "./App.css";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// 🎨 Chart Renderer — shared utility
function renderChart(mergedData, chartType, xKey, yKey) {
  if (!mergedData?.length || !xKey || !yKey)
    return <p className="placeholder">Select X and Y fields.</p>;

  switch (chartType) {
    case "bar":
      return (
        <BarChart data={mergedData}>
          <XAxis dataKey={xKey} stroke="#2E2A27" />
          <YAxis stroke="#2E2A27" />
          <Tooltip />
          <Legend />
          <Bar dataKey={yKey} fill="#4B584E" radius={[6, 6, 0, 0]} />
        </BarChart>
      );
    case "line":
      return (
        <LineChart data={mergedData}>
          <XAxis dataKey={xKey} stroke="#2E2A27" />
          <YAxis stroke="#2E2A27" />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey={yKey}
            stroke="#2E4D30"
            strokeWidth={2}
          />
        </LineChart>
      );
    case "pie":
      return (
        <PieChart>
          <Pie
            data={mergedData}
            dataKey={yKey}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius={110}
            fill="#4B584E"
            label
          >
            {mergedData.map((_, i) => (
              <Cell
                key={i}
                fill={["#4B584E", "#2E4D30", "#A58E74", "#B2A38D"][i % 4]}
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      );
    default:
      return <p>Unsupported chart type.</p>;
  }
}

// 🧠 AI Message Component (handles table + chart)
function AIMessage({ msg }) {
  const mergedData = Array.isArray(msg.data?.merged_results)
    ? msg.data.merged_results
    : [];

  const keys = mergedData.length ? Object.keys(mergedData[0]) : [];
  const numericKeys = keys.filter((k) =>
    mergedData.some((r) => typeof r[k] === "number")
  );
  const stringKeys = keys.filter(
    (k) => typeof mergedData[0]?.[k] === "string"
  );

  const [chartType, setChartType] = useState("bar");
  const [xKey, setXKey] = useState(stringKeys[0] || "");
  const [yKey, setYKey] = useState(numericKeys[0] || "");

  useEffect(() => {
    if (!xKey && stringKeys[0]) setXKey(stringKeys[0]);
    if (!yKey && numericKeys[0]) setYKey(numericKeys[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msg.data]);

  // Excel Export
  const downloadExcel = () => {
    if (!mergedData?.length) return alert("No data to download.");
    const flattened = mergedData.map((row) => {
      const cleanRow = {};
      Object.entries(row).forEach(([k, v]) => {
        cleanRow[k] =
          Array.isArray(v)
            ? v.join(", ")
            : typeof v === "object" && v !== null
            ? JSON.stringify(v)
            : v;
      });
      return cleanRow;
    });
    const ws = XLSX.utils.json_to_sheet(flattened);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, "query_results.xlsx");
  };

  return (
    <div className="message ai-msg">
      <h3>✅ Query executed successfully</h3>
      <p>
        <strong>Databases:</strong>{" "}
        {Array.isArray(msg.data?.selected_databases)
          ? msg.data.selected_databases.join(", ")
          : String(msg.data?.selected_databases || "")}
      </p>

      {mergedData.length === 0 && (
        <p className="no-data">
          No matching records found in any selected databases.
        </p>
      )}

      {mergedData.length > 0 && (
        <>
          <div className="actions-bar">
            <button className="download-btn" onClick={downloadExcel}>
              ⬇ Download Excel
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  {keys.map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mergedData.slice(0, 50).map((row, i) => (
                  <tr key={i}>
                    {keys.map((k, j) => (
                      <td key={j}>
                        {row[k] === null || row[k] === undefined
                          ? ""
                          : String(row[k])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="chart-controls">
            <select
              value={chartType}
              onChange={(e) => setChartType(e.target.value)}
            >
              <option value="bar">Bar</option>
              <option value="line">Line</option>
              <option value="pie">Pie</option>
            </select>
            <select value={xKey} onChange={(e) => setXKey(e.target.value)}>
              <option value="">Select X (string)</option>
              {stringKeys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
            <select value={yKey} onChange={(e) => setYKey(e.target.value)}>
              <option value="">Select Y (number)</option>
              {numericKeys.map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
          </div>

          <div className="chart-box">
            <ResponsiveContainer width="100%" height={300}>
              {renderChart(mergedData, chartType, xKey, yKey)}
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

// 💬 Main Chat App
function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // ✅ Phase 1: Session ID management
  const [sessionId] = useState(() => {
    const existing = localStorage.getItem("sessionId");
    if (existing) return existing;
    const newId = crypto.randomUUID();
    localStorage.setItem("sessionId", newId);
    return newId;
  });

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 🔍 Submit query
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMsg = { type: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setLoading(true);

    try {
      // ✅ Send sessionId with every request (Phase 1)
      const res = await axios.post("http://127.0.0.1:8000/api/multi-db-query", {
        query,
        session_id: sessionId,
      });

      const aiMsg = {
        type: "ai",
        status: res.data.status,
        data: res.data,
        text: res.data.message || "",
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      const msgText =
        error?.response?.data?.message || error?.message || "Network error";
      setMessages((prev) => [
        ...prev,
        {
          type: "ai",
          status: "error",
          text: msgText,
          data: error?.response?.data,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>Talk2Data Interactive Chat</h1>
        <small className="session-tag">Session ID: {sessionId}</small>
      </header>

      <div className="chat-window">
        {messages.map((msg, index) => {
          if (msg.type === "user") {
            return (
              <div key={index} className="message user-msg">
                <p>{msg.text}</p>
              </div>
            );
          }

          if (msg.type === "ai" && msg.status === "success") {
            return <AIMessage key={index} msg={msg} />;
          }

          if (msg.type === "ai" && msg.status === "info") {
            return (
              <div key={index} className="message ai-msg">
                <p>{msg.text}</p>
              </div>
            );
          }

          if (msg.type === "ai" && msg.status === "error") {
            return (
              <div key={index} className="message ai-msg error-style">
                <h3>⚠️ Query Error</h3>
                <p>{msg.text}</p>
              </div>
            );
          }

          return null;
        })}

        {loading && (
          <div className="message ai-msg typing">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <textarea
          placeholder="Ask your query (e.g., Show me each dish and its calories)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        ></textarea>
        <button type="submit" disabled={loading}>
          {loading ? "Processing..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default App;
