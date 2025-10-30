import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Particles } from "@/components/ui/particles";
import { AIInputWithFile } from "@/components/ui/ai-input-with-file";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowLeft, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/components/chat/ChatMessage";

type Discrepancy = {
  name: string;
  details: string;
};

type CompareReport = {
  summary: string;
  discrepancy: Discrepancy[];
};

export default function Report() {
  const location = useLocation();
  const navigate = useNavigate();
  const report = (location.state as { report?: CompareReport } | null)?.report;

  // Fallback if navigated directly without state
  useEffect(() => {
    if (!report) {
      navigate("/", { replace: true });
    }
  }, [report, navigate]);

  const differences = useMemo(() => report?.discrepancy ?? [], [report]);

  // Chat state
  const [messages, setMessages] = useState<{ role: "assistant" | "user"; content: string }[]>([
    {
      role: "assistant",
      content:
        "Hi! I generated a quick summary and highlighted differences. Ask me anything about this verification.",
    },
  ]);
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when messages change
    listRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const send = () => {
    const text = input.trim();
    if (!text) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    // Simple mock assistant reply
    const reply =
      text.toLowerCase().includes("summary")
        ? `Summary: ${report?.summary ?? "No summary"}`
        : differences.length
        ? `Top flagged item: ${differences[0].name} — ${differences[0].details}`
        : "No discrepancies found.";
    setTimeout(() => setMessages((m) => [...m, { role: "assistant", content: reply }]), 400);
  };

  const dot = (idx: number) => (idx === 0 ? "bg-red-500" : "bg-amber-400");

  if (!report) return null;

  return (
    <div className="relative min-h-screen bg-background overflow-hidden">
      <Particles className="absolute inset-0 z-0" quantity={90} staticity={60} size={1} color="#6F00FF" />

      <div className="relative z-10 container mx-auto px-6 py-10 max-w-5xl">
        <Link 
          to="/" 
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Home
        </Link>
        {/* Header */}
        <header className="mb-6">
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-foreground leading-tight">
            Verification Report
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            AI-powered comparison result
          </p>
        </header>

        {/* Summary - plain text */}
        <section className="rounded-xl border bg-card p-5 md:p-6 mb-6">
          <p className="text-sm text-foreground leading-relaxed">
            {report.summary}
          </p>
        </section>

        {/* Differences */}
        <section className="mb-28">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-foreground">Differences & Flags</h2>
            <span className="text-xs text-muted-foreground">{differences.length} findings</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {differences.map((d, i) => (
              <article key={`${d.name}-${i}`} className="rounded-xl border bg-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn("inline-block h-2.5 w-2.5 rounded-full shrink-0", dot(i))} />
                  <div className="font-medium text-foreground">{d.name}</div>
                  {d.details && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger className="ml-auto inline-flex items-center text-muted-foreground hover:text-foreground">
                          <Info className="h-4 w-4" />
                        </TooltipTrigger>
                        <TooltipContent sideOffset={6} className="max-w-xs text-xs leading-relaxed">
                          {d.details}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
                <div className="text-sm text-foreground">
                  {d.details}
                </div>
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
          <div className="space-y-3">
            {messages.map((m, i) => (
              <div key={i} className="flex">
                <ChatMessage role={m.role} content={m.content} />
              </div>
            ))}
            <div ref={listRef} />
          </div>
        </section>
      </div>

      {/* Chat input */}
      <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50">
        <AIInputWithFile
          onSubmit={(msg) => {
            if (!msg.trim()) return;
            setMessages((m) => [...m, { role: "user", content: msg }]);
            setTimeout(() => setMessages((m) => [...m, { role: "assistant", content: "Got it. Let me analyze that for you." }]), 300);
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
