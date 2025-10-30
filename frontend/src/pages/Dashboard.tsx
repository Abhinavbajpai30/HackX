import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/dashboard/DataTable";
import { InsightsSidebar } from "@/components/dashboard/InsightsSidebar";
import { CheckCircle, AlertTriangle, Download, Network, MessageSquare } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuthValidation } from "@/hooks/use-auth-validation";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { dashboardDemo } from "@/data/dashboard-demo";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import NavBar from "@/components/layout/NavBar";
import ChatSidebar from "@/components/layout/ChatSidebar";
interface Message {
  role: "user" | "assistant";
  content: string;
}

const Dashboard = () => {
  const navigate = useNavigate();
  useAuthValidation();
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I've analyzed your documents. Ask me anything about the verification results." }
  ]);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return true;
    return localStorage.getItem('sidebarOpen') !== 'false';
  });

  const handleChatSend = () => {
    if (!chatInput.trim()) return;
    setChatMessages(prev => [
      ...prev,
      { role: "user" as const, content: chatInput },
      { role: "assistant" as const, content: "I can help explain the discrepancies or provide more details about the verification results." }
    ]);
    setChatInput("");
  };

  return (
    <div className="relative min-h-screen bg-background overflow-hidden">
      <NavBar />
      <ChatSidebar onToggle={setIsSidebarOpen} />

      {/* Main Content */}
      <div className={`relative z-10 container mx-auto ${isSidebarOpen ? 'pl-24' : 'px-6'} pt-20 pb-10`}>
        {/* Page header actions */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-foreground">Verification Dashboard</h1>
          <div className="flex gap-3">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="outline" className="rounded-full gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Ask AI
                </Button>
              </SheetTrigger>
              <SheetContent className="w-[400px] sm:w-[540px]">
                <SheetHeader>
                  <SheetTitle>AI Assistant</SheetTitle>
                </SheetHeader>
                <div className="flex flex-col h-full pt-6">
                  <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                    {chatMessages.map((msg, idx) => (
                      <ChatMessage key={idx} role={msg.role} content={msg.content} />
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Ask about the verification results..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyPress={(e) => e.key === "Enter" && handleChatSend()}
                      className="rounded-full"
                    />
                    <Button onClick={handleChatSend} size="icon" className="rounded-full">
                      <MessageSquare className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </SheetContent>
            </Sheet>
            <Button variant="outline" className="rounded-full gap-2">
              <CheckCircle className="w-4 h-4" />
              Approve All
            </Button>
            <Button variant="outline" className="rounded-full gap-2">
              <AlertTriangle className="w-4 h-4" />
              Flagged
            </Button>
            <Button onClick={() => navigate('/vendor-graph')} variant="outline" className="rounded-full gap-2">
              <Network className="w-4 h-4" />
              Graph
            </Button>
            <Button className="rounded-full gap-2 bg-gradient-peach text-white">
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1fr_320px] gap-8">
          {/* Left: Data Table */}
          <div className="space-y-6">
            {/* Summary Stats (bound to backend demo JSON) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Total Documents</p>
                <p className="text-3xl font-bold text-foreground">{dashboardDemo.document_summary.total_documents}</p>
                <p className="text-xs text-muted-foreground mt-1">POs: {dashboardDemo.document_summary.total_purchase_orders} · Invoices: {dashboardDemo.document_summary.total_invoices}</p>
              </div>
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Total Value</p>
                <p className="text-3xl font-bold text-foreground">{dashboardDemo.document_summary.total_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                <p className="text-xs text-muted-foreground mt-1">Avg Invoice: {dashboardDemo.document_summary.average_invoice_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
              </div>
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm text-muted-foreground mb-1">Vendors</p>
                <p className="text-3xl font-bold text-foreground">{dashboardDemo.document_summary.unique_vendors}</p>
                <p className="text-xs text-muted-foreground mt-1">Linked Ratio: {dashboardDemo.document_summary.linked_invoice_to_po_ratio}</p>
              </div>
            </div>

            {/* Compact charts matching current vibe */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-4">Document Distribution</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <RechartsTooltip />
                      <Pie
                        data={[...dashboardDemo.graphs.documents.document_type_distribution]}
                        dataKey="value"
                        nameKey="label"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={4}
                      >
                        {[...dashboardDemo.graphs.documents.document_type_distribution].map((_, idx) => (
                          <Cell key={idx} fill={["hsl(var(--primary))", "hsl(var(--accent-foreground))"][idx % 2]} />
                        ))}
                      </Pie>
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-4">Monthly Spending Trend</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={[...dashboardDemo.graphs.temporal.monthly_spending_trend]}>
                      <defs>
                        <linearGradient id="primaryArea" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="x" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip />
                      <Area type="monotone" dataKey="y" stroke="hsl(var(--primary))" fill="url(#primaryArea)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Financials and Vendors */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-4">Cost Composition</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[...dashboardDemo.graphs.financials.cost_composition]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="label" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip />
                      <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                        {[...dashboardDemo.graphs.financials.cost_composition].map((d, idx) => (
                          <Cell
                            key={idx}
                            fill={
                              d.label === "Subtotal"
                                ? "hsl(var(--primary))"
                                : d.label === "Tax"
                                ? "hsl(var(--accent-foreground))"
                                : "hsl(var(--muted-foreground))"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-4">Top Vendors by Value</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[...dashboardDemo.graphs.vendors.top_vendors_chart]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="x" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip />
                      <Bar dataKey="y" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Discrepancies and Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-4">Discrepancy Trend</p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={[...dashboardDemo.graphs.discrepancies.discrepancy_trend]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="x" stroke="hsl(var(--muted-foreground))" />
                      <YAxis stroke="hsl(var(--muted-foreground))" />
                      <RechartsTooltip />
                      <Line type="monotone" dataKey="y" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border">
                <p className="text-sm font-medium text-foreground mb-2">Most Recent Summary</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{dashboardDemo.discrepancy_insights.most_recent_summary}</p>
              </div>
            </div>

            {/* Data Table */}
            <DataTable />

            {/* Footer Info */}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <p>Updated: 2 minutes ago</p>
              <p>Showing 4 of 124 invoices</p>
            </div>
          </div>

          {/* Right: Insights Sidebar */}
          <div>
            <InsightsSidebar />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
