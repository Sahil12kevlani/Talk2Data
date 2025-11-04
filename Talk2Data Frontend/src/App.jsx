import React, { useState } from "react";
import axios from "axios";
import * as XLSX from "xlsx";
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

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [chartType, setChartType] = useState("bar");
  const [xKey, setXKey] = useState("");
  const [yKey, setYKey] = useState("");

  // === Handle Query Submission ===
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setResponse(null);

    try {
      const res = await axios.post(
        `http://127.0.0.1:8000/api/multi-db-query?query=${encodeURIComponent(query)}`
      );
      setResponse(res.data);
    } catch (error) {
      setResponse({ status: "error", message: error.message });
    } finally {
      setLoading(false);
    }
  };

  // === Excel Download ===
  const downloadExcel = (data) => {
    if (!data || data.length === 0) {
      alert("No data to download.");
      return;
    }
    const flattened = data.map((row) => ({
      ...row,
      _source_dbs: Array.isArray(row._source_dbs)
        ? row._source_dbs.join(", ")
        : row._source_dbs,
    }));

    const ws = XLSX.utils.json_to_sheet(flattened);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, "query_results.xlsx");
  };

  // === Extract Possible Chart Keys ===
  const mergedData = response?.merged_results || [];
  const keys = mergedData.length > 0 ? Object.keys(mergedData[0]) : [];

  const numericKeys = keys.filter((key) =>
    mergedData.some((row) => typeof row[key] === "number")
  );
  const stringKeys = keys.filter(
    (key) => typeof mergedData[0]?.[key] === "string"
  );

  // === Render Chart Dynamically ===
  const renderChart = () => {
    if (!xKey || !yKey) return <p>Select X and Y fields to visualize.</p>;
    switch (chartType) {
      case "bar":
        return (
          <BarChart data={mergedData}>
            <XAxis dataKey={xKey} stroke="#ccc" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey={yKey} fill="#3b82f6" />
          </BarChart>
        );
      case "line":
        return (
          <LineChart data={mergedData}>
            <XAxis dataKey={xKey} stroke="#ccc" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey={yKey} stroke="#10b981" />
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
              fill="#8b5cf6"
              label
            >
              {mergedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={[
                    "#3b82f6",
                    "#10b981",
                    "#f59e0b",
                    "#ef4444",
                    "#8b5cf6",
                  ][index % 5]}
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
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center p-6">
      {/* Header */}
      <h1 className="text-4xl font-bold mb-8 text-center text-blue-400">
        Talk2Data Chat Interface
      </h1>

      {/* Query Form */}
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-3xl bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl"
      >
        <textarea
          className="w-full p-4 rounded-lg bg-gray-800 border border-gray-700 text-white focus:outline-none focus:border-blue-500"
          rows="4"
          placeholder="Type your query (e.g. Show me each dish and its calories)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        ></textarea>

        <button
          type="submit"
          className={`mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition ${
            loading ? "opacity-70 cursor-not-allowed" : ""
          }`}
          disabled={loading}
        >
          {loading ? "Processing..." : "Send Query"}
        </button>
      </form>

      {/* Results */}
      {response && (
        <div className="w-full max-w-5xl mt-10 bg-gray-900 p-8 rounded-2xl border border-gray-800 shadow-xl">
          {response.status === "success" ? (
            <>
              <p className="text-green-400 font-semibold mb-4 text-lg">
                ✅ Query executed successfully
              </p>
              <p className="text-gray-300 mb-4">
                <strong>Selected Databases:</strong>{" "}
                {response.selected_databases.join(", ")}
              </p>

              {/* Excel Download */}
              {mergedData.length > 0 && (
                <button
                  className="bg-green-600 hover:bg-green-700 px-5 py-2 rounded-lg text-white font-medium mb-6"
                  onClick={() => downloadExcel(mergedData)}
                >
                  Download Excel
                </button>
              )}

              {/* === Dynamic Chart Controls === */}
              {mergedData.length > 0 && (
                <div className="bg-gray-950 p-6 rounded-2xl mt-6">
                  <h2 className="text-2xl text-blue-400 font-semibold mb-4">
                    📊 Visual Insights
                  </h2>

                  <div className="flex flex-wrap gap-4 mb-6">
                    <select
                      className="bg-gray-800 border border-gray-700 rounded-lg p-2"
                      value={chartType}
                      onChange={(e) => setChartType(e.target.value)}
                    >
                      <option value="bar">Bar Chart</option>
                      <option value="line">Line Chart</option>
                      <option value="pie">Pie Chart</option>
                    </select>

                    <select
                      className="bg-gray-800 border border-gray-700 rounded-lg p-2"
                      value={xKey}
                      onChange={(e) => setXKey(e.target.value)}
                    >
                      <option value="">Select X-Axis</option>
                      {stringKeys.map((key) => (
                        <option key={key} value={key}>
                          {key}
                        </option>
                      ))}
                    </select>

                    <select
                      className="bg-gray-800 border border-gray-700 rounded-lg p-2"
                      value={yKey}
                      onChange={(e) => setYKey(e.target.value)}
                    >
                      <option value="">Select Y-Axis</option>
                      {numericKeys.map((key) => (
                        <option key={key} value={key}>
                          {key}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="h-96 bg-gray-900 rounded-xl p-4 border border-gray-800 shadow-md">
                    <ResponsiveContainer width="100%" height="100%">
                      {renderChart()}
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-red-400">❌ {response.message}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
