import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Particles } from "@/components/ui/particles";
import { AIInputWithFile } from "@/components/ui/ai-input-with-file";
import { ArrowLeft, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { Button } from "@/components/ui/button";
import NavBar from "@/components/layout/NavBar";
import ChatSidebar from "@/components/layout/ChatSidebar";

type Discrepancy = {
  name: string;
  details: string;
};

type CompareResponse = {
  id?: number;
  vendor_id?: string | null;
  discrepancy: Discrepancy[];
  summary: string;
  messages?: { role: "assistant" | "user"; content: string }[];
};

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const state = location.state as { report?: CompareResponse } | null;
  
  const [report, setReport] = useState<CompareResponse | undefined>(state?.report);
  const [loading, setLoading] = useState(!state?.report);
  
  const reportId: number | undefined = report?.id || (id ? parseInt(id) : undefined);
  const discrepancies: Discrepancy[] = report?.discrepancy ?? [];
  const vendorId: string | null = report?.vendor_id ?? null;
  const summaryText: string = report?.summary ?? "No summary available.";

  // Chat state
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; content: string }[]>([]);
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  // Load report data from API if not passed via state
  useEffect(() => {
    const loadReport = async () => {
      if (!reportId || report) return;
      
      try {
        setLoading(true);
        const response = await fetch(`${import.meta.env?.VITE_BACKEND_URL}/reports/${reportId}`, {
          headers: {
            "ngrok-skip-browser-warning": "true",
          },
        });
        
        if (!response.ok) {
          throw new Error("Failed to load report");
        }
        
        const data = await response.json();
        setReport(data);
        
        // Load messages from the response
        if (data.messages && Array.isArray(data.messages)) {
          setMessages(data.messages);
        } else {
          // Fallback to default welcome message
          setMessages([{
            role: "assistant",
            content: "Hi! I generated a quick summary and highlighted differences. Ask me anything about this verification.",
          }]);
        }
      } catch (error) {
        console.error("Error loading report:", error);
        // Set default message on error
        setMessages([{
          role: "assistant",
          content: "Hi! I generated a quick summary and highlighted differences. Ask me anything about this verification.",
        }]);
      } finally {
        setLoading(false);
      }
    };
    
    loadReport();
  }, [reportId]);

  // Initialize messages from report if passed via state
  useEffect(() => {
    if (report?.messages && Array.isArray(report.messages) && messages.length === 0) {
      setMessages(report.messages);
    } else if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: "Hi! I generated a quick summary and highlighted differences. Ask me anything about this verification.",
      }]);
    }
  }, [report]);

  useEffect(() => {
    // Scroll to bottom when messages change
    listRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const sendMessage = async (message: string) => {
    if (!message.trim() || !reportId) return;
    
    setMessages((m) => [...m, { role: "user", content: message }]);
    
    try {
      const response = await fetch(`${import.meta.env?.VITE_BACKEND_URL}/message/${reportId}`, {
        method: "POST",
        headers: {
          "ngrok-skip-browser-warning": "true",
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ role: "user", content: message }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to send message");
      }
      
      const data = await response.json();
      setMessages((m) => [...m, { role: "assistant", content: data.response || "I understand your question." }]);
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((m) => [...m, { role: "assistant", content: "Sorry, I encountered an error processing your message." }]);
    }
  };

  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return localStorage.getItem('sidebarOpen') !== 'false';
  });

  const handleDownloadCSV = () => {
    const headers = ["Name", "Details"];
    const rows = discrepancies.map((d) => [
      d.name.replace(/,/g, " "),
      (d.details || "").replace(/\n|,/g, " "),
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `verification-report-${vendorId || "report"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative min-h-screen bg-background overflow-hidden">
      <Particles className="absolute inset-0 z-0" quantity={90} staticity={60} size={1} color="#6F00FF" />
      <NavBar />
      <ChatSidebar onToggle={setIsSidebarOpen} />

      <div className={`relative z-10 container mx-auto ${isSidebarOpen ? 'pl-24' : 'px-6'} pt-20 pb-10 max-w-5xl`}>
        <Link 
          to="/" 
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Link>
        {/* Header */}
        <header className="mb-6">
          <div className="flex items-center justify-between gap-3">
            <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground leading-tight">
              Verification Report
            </h1>
            <Button variant="outline" className="rounded-full" onClick={handleDownloadCSV}>
              <Download className="h-4 w-4 mr-2" />
              Download CSV
            </Button>
          </div>
          {vendorId && (
            <p className="text-sm text-muted-foreground mt-1">Vendor: {vendorId}</p>
          )}
        </header>

        {/* Summary - plain text */}
        <section className="rounded-xl border bg-card p-5 md:p-6 mb-6">
          <p className="text-sm text-foreground leading-relaxed">{summaryText}</p>
        </section>

        {/* Differences */}
        <section className="mb-28">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-foreground">Differences & Flags</h2>
            <span className="text-xs text-muted-foreground">{discrepancies.length} findings</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {discrepancies.map((d, idx) => (
              <article key={idx} className="rounded-xl border bg-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn("inline-block h-2.5 w-2.5 rounded-full shrink-0", "bg-emerald-500")} />
                  <div className="font-medium text-foreground">{d.name}</div>
                </div>
                <p className="text-sm text-muted-foreground">{d.details}</p>
              </article>
            ))}
          </div>
        </section>

        {/* Divider between report content and chat */}
        <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
          <div className="flex-1 border-t" />
          <span>Conversation</span>
          <div className="flex-1 border-t" />
        </div>

        {/* Messages */}
        <section className="pb-40">
          <h3 className="sr-only">Conversation</h3>
          <div className="space-y-3 bg-background/50 p-4 rounded-lg">
            {messages.map((m, i) => (
              <div key={i} className="flex">
                <ChatMessage role={m.role} content={m.content} />
              </div>
            ))}
            {/* Anchor + spacer to ensure we can scroll past the fixed input */}
            <div ref={listRef} className="h-20" aria-hidden />
          </div>
        </section>
      </div>

      {/* Chat input */}
      <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50">
        <AIInputWithFile
          onSubmit={(msg) => {
            sendMessage(msg);
          }}
          className="border bg-card rounded-2xl px-0"
        />
      </div>
    </div>
  );
}

function Field({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className={cn("rounded-lg border bg-card p-3", className)}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium text-foreground break-words">{value}</div>
    </div>
  );
}