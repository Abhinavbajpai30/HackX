import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { AuthService } from "@/lib/auth";

const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || "http://localhost:8000";

type Discrepancy = {
  name: string;
  details: string;
};

type ReportItem = {
  vendor_id?: string | null;
  discrepancy: Discrepancy[];
  summary: string;
};

export default function ChatSidebar({ className = "", onToggle }: { className?: string; onToggle?: (open: boolean) => void }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState<boolean>(() => {
    const v = typeof window !== "undefined" ? localStorage.getItem("sidebarOpen") : null;
    return v !== "false"; // default open
  });

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem("sidebarOpen", String(open));
    onToggle?.(open);
  }, [open, onToggle]);

  useEffect(() => {
    const fetchReports = async () => {
      setLoading(true);
      setError(null);
      try {
        const headers: HeadersInit = { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" };
        const token = AuthService.getToken();
        if (token) headers["Authorization"] = `Bearer ${token}`;
        const res = await fetch(`${BACKEND_URL}/reports`, { headers });
        if (!res.ok) throw new Error(`Failed to fetch reports: ${res.status}`);
        const data = (await res.json()) as ReportItem[];
        setReports(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error(e);
        setError("Unable to load reports");
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  const openReport = (report: ReportItem) => {
    navigate("/report", { state: { report } });
  };

  return (
    <aside
      className={cn(
        "fixed top-14 left-0 z-30 h-[calc(100vh-56px)] transition-all duration-300 border-t",
        open ? "w-72" : "w-0",
        className
      )}
      aria-hidden={!open}
    >
      {/* Panel */}
      <div className={cn("h-full border-r bg-background overflow-hidden", open ? "opacity-100" : "opacity-0")}>        
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="font-semibold text-sm text-foreground">Reports</div>
          <button
            onClick={() => setOpen(false)}
            className="p-1 rounded hover:bg-accent"
            aria-label="Close sidebar"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        </div>

        <div className="p-2 space-y-1">
          {loading && (
            <div className="text-xs text-muted-foreground px-3 py-2">Loading…</div>
          )}
          {error && (
            <div className="text-xs text-red-500 px-3 py-2">{error}</div>
          )}
          {!loading && !error && reports.length === 0 && (
            <div className="text-xs text-muted-foreground px-3 py-2">No reports yet.</div>
          )}
          {reports.map((r, idx) => (
            <button
              key={idx}
              onClick={() => openReport(r)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent text-left"
            >
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <span className="truncate text-sm">
                {r.vendor_id || (r.summary ? r.summary.slice(0, 40) + (r.summary.length > 40 ? "…" : "") : "Report")}
              </span>
            </button>
          ))}
        </div>

        <div className="absolute bottom-3 left-0 right-0 px-3">
          <Link to="/" className="block text-xs text-muted-foreground text-center hover:underline">
            Home
          </Link>
        </div>
      </div>

      {/* Re-open handle */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className={cn(
            "fixed top-14 left-0 z-40 h-10 w-5 flex items-center justify-center",
            "bg-background/80 hover:bg-background transition-all duration-200 ease-in-out",
            "border-r border-t border-border/50 hover:border-border",
            "shadow-sm hover:shadow-md backdrop-blur-sm",
            "group"
          )}
          aria-label="Open sidebar"
        >
          <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
        </button>
      )}
    </aside>
  );
}
