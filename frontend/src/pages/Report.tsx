import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Particles } from "@/components/ui/particles";
import { AIInputWithFile } from "@/components/ui/ai-input-with-file";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowLeft, Download, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { Button } from "@/components/ui/button";
import NavBar from "@/components/layout/NavBar";
import ChatSidebar from "@/components/layout/ChatSidebar";

type Difference = {
  id: string;
  field: string;
  invoice: string | number | null;
  po: string | number | null;
  severity: "low" | "medium" | "high";
  note: string;
  recommendation?: string;
};

export default function Report() {
  // Dummy, replace with backend payload later
  const summary = useMemo(
    () => ({
      vendor: "Acme Supplies Pvt Ltd",
      invoiceNumber: "INV-2025-0142",
      poNumber: "PO-22915",
      invoiceDate: "2025-10-02",
      dueDate: "2025-11-01",
      currency: "INR",
      total: 128450.0,
      items: 7,
      taxes: "GST 18%",
      status: "Pending Review",
    }),
    [],
  );

  const differences: Difference[] = useMemo(
    () => [
      {
        id: "qty-line-3",
        field: "Quantity (Line 3)",
        invoice: 120,
        po: 100,
        severity: "high",
        note: "Invoice shows 20 more units than PO.",
        recommendation: "Verify delivery challan and adjust bill or raise a debit note.",
      },
      {
        id: "rate-item-5",
        field: "Rate (Item 5)",
        invoice: "₹1,250.00",
        po: "₹1,200.00",
        severity: "medium",
        note: "Rate increased by 4.2% vs. PO.",
        recommendation: "Confirm revised quote or apply PO rate.",
      },
      {
        id: "gst-mismatch",
        field: "GST Split",
        invoice: "18% IGST",
        po: "9% CGST + 9% SGST",
        severity: "low",
        note: "Tax structure differs; total tax equal.",
        recommendation: "Confirm place-of-supply and company GST registrations.",
      },
    ],
    [],
  );

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
        ? `Summary: Vendor ${summary.vendor}, Invoice ${summary.invoiceNumber} vs PO ${summary.poNumber}. Total ₹${summary.total.toLocaleString()} ${summary.currency}. ${differences.length} potential issues.`
        : `Top flagged item: ${differences[0].field} — ${differences[0].note}`;
    setTimeout(() => setMessages((m) => [...m, { role: "assistant", content: reply }]), 400);
  };

  const dot = (s: Difference["severity"]) => (s === "high" ? "bg-red-500" : "bg-amber-400");
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return localStorage.getItem('sidebarOpen') !== 'false';
  });

  const handleDownloadCSV = () => {
    const headers = ["Field", "Invoice", "PO", "Severity", "Note", "Recommendation"]; 
    const rows = differences.map((d) => [
      d.field.replace(/,/g, " "),
      String(d.invoice).replace(/,/g, ""),
      String(d.po).replace(/,/g, ""),
      d.severity,
      (d.note || "").replace(/\n|,/g, " "),
      (d.recommendation || "").replace(/\n|,/g, " "),
    ]);

    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `verification-report-${summary.invoiceNumber}.csv`;
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
          <p className="text-sm text-muted-foreground mt-1">
            Invoice {summary.invoiceNumber} vs PO {summary.poNumber}
          </p>
        </header>

        {/* Summary - plain text */}
        <section className="rounded-xl border bg-card p-5 md:p-6 mb-6">
          <p className="text-sm text-foreground leading-relaxed">
            Vendor <span className="font-medium">{summary.vendor}</span> — Invoice <span className="font-medium">{summary.invoiceNumber}</span> vs PO <span className="font-medium">{summary.poNumber}</span>. Issued on <span className="font-medium">{summary.invoiceDate}</span>, due by <span className="font-medium">{summary.dueDate}</span>. Total <span className="font-medium">₹{summary.total.toLocaleString()} {summary.currency}</span> for <span className="font-medium">{summary.items}</span> items, taxes: <span className="font-medium">{summary.taxes}</span>. Status: <span className="font-medium">{summary.status}</span>.
          </p>
        </section>

        {/* Differences */}
        <section className="mb-28">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-foreground">Differences & Flags</h2>
            <span className="text-xs text-muted-foreground">{differences.length} findings</span>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {differences.map((d) => (
              <article key={d.id} className="rounded-xl border bg-card p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className={cn("inline-block h-2.5 w-2.5 rounded-full shrink-0", dot(d.severity))} />
                  <div className="font-medium text-foreground">{d.field.replace(/\s*\(.*\)/, "")}</div>
                  {d.recommendation && (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger className="ml-auto inline-flex items-center text-muted-foreground hover:text-foreground">
                          <Info className="h-4 w-4" />
                        </TooltipTrigger>
                        <TooltipContent sideOffset={6} className="max-w-xs text-xs leading-relaxed">
                          {d.recommendation}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}
                </div>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Invoice</dt>
                    <dd className="font-medium break-words">{String(d.invoice)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">PO</dt>
                    <dd className="font-medium break-words">{String(d.po)}</dd>
                  </div>
                </dl>
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